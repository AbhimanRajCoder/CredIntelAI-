"""
Research Agent Orchestrator for Intelli-Credit.
Main LangGraph node that coordinates the full corporate intelligence pipeline.

Pipeline:
    1. Check cache
    2. Generate queries
    3. Fetch data (SerpAPI + GNews)
    4. Filter sources
    10. Store in Pinecone
    6. Extract signals (LLM)
    7. Analyze promoter (LLM)
    8. Analyze sector (LLM)
    9. Compute research score
    10. Build state + cache results
"""

import logging
from typing import Dict, Any, List

from app.models.schemas import ResearchSignals, ResearchReport, AnalysisStatus
from app.services.serp_search import get_serp_service
from app.services.news_search import get_gnews_service
from app.services.research_cache import get_research_cache
from app.db.pinecone_store import get_pinecone_store

from app.agents.research.query_generator import generate_research_queries, flatten_queries
from app.agents.research.source_filter import filter_results
from app.agents.research.signal_extractor import extract_signals
from app.agents.research.promoter_intel import analyze_promoter
from app.agents.research.sector_intel import analyze_sector
from app.agents.research.scoring_engine import compute_research_score

logger = logging.getLogger(__name__)


async def research_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Corporate Intelligence Research Agent — LangGraph node.

    Orchestrates a multi-source intelligence pipeline:
    - SerpAPI + GNews data acquisition
    - Source credibility filtering
    - LLM-based signal extraction
    - Dedicated promoter & sector analysis
    - Numerical research scoring
    - Pinecone traceability
    - 24-hour result caching
    """
    logger.info("=" * 60)
    logger.info("RESEARCH AGENT v2: Starting corporate intelligence pipeline")
    logger.info("=" * 60)

    company_name = state.get("company_name", "")
    sector = state.get("sector", "")
    analysis_id = state.get("analysis_id", "")
    errors = state.get("errors", [])

    research_signals = ResearchSignals()

    try:
        # ── Step 0: Check cache ──────────────────────────────────────────────
        cache = get_research_cache()
        cached = cache.get_cached(company_name)
        if cached:
            logger.info("Using cached research results")
            return {
                **state,
                "research_signals": cached,
                "status": AnalysisStatus.RESEARCHING.value,
                "current_agent": "research_agent",
                "errors": errors,
            }

        # ── Step 1: Generate queries ─────────────────────────────────────────
        fin_metrics = state.get("financial_metrics", {})
        promoter_names = fin_metrics.get("promoter_names", [])
        
        categorized_queries = generate_research_queries(
            company_name, 
            sector, 
            promoter_names=promoter_names
        )
        all_queries = flatten_queries(categorized_queries)

        logger.info(f"Generated {len(all_queries)} search queries")

        # ── Step 2: Fetch data from SerpAPI ──────────────────────────────────
        serp = get_serp_service()

        all_snippets: List[str] = []
        all_sources: List[str] = []
        promoter_snippets: List[str] = []
        sector_snippets: List[str] = []
        litigation_snippets: List[str] = []

        for category, queries in categorized_queries.items():
            for query in queries:
                results = await serp.search(query, num_results=5)

                # Apply source credibility filter (lenient mode: keep all but tag)
                results = filter_results(results, url_key="link", strict=False)

                for r in results:
                    snippet = r.get("snippet", "")
                    link = r.get("link", "")
                    source_label = r.get("title", "")

                    if snippet:
                        tagged_snippet = f"[{source_label}] {snippet}"
                        all_snippets.append(tagged_snippet)

                        if category == "promoter":
                            promoter_snippets.append(tagged_snippet)
                        elif category == "sector":
                            sector_snippets.append(tagged_snippet)
                        elif category == "litigation":
                            litigation_snippets.append(tagged_snippet)

                    if link:
                        all_sources.append(link)

        # ── Step 2b: Fetch data from GNews (if configured) ───────────────────
        gnews = get_gnews_service()
        if gnews.enabled:
            news_queries = [
                f"{company_name} India news",
                f"{company_name} financial controversy",
                f"{sector} sector India outlook",
            ]
            news_articles = await gnews.search_batch(news_queries, max_per_query=5)

            news_articles = filter_results(news_articles, url_key="url", strict=False)

            for article in news_articles:
                desc = article.get("description", "")
                title = article.get("title", "")
                source_name = article.get("source_name", "")
                url = article.get("url", "")

                if desc:
                    tagged = f"[{source_name}: {title}] {desc}"
                    all_snippets.append(tagged)
                if url:
                    all_sources.append(url)

            logger.info(f"GNews contributed {len(news_articles)} articles")

        # Deduplicate sources
        unique_sources = list(set(all_sources))
        article_count = len(all_snippets)

        logger.info(
            f"Total data: {article_count} snippets, "
            f"{len(unique_sources)} unique sources"
        )

        # ── Step 3: Store in Pinecone for traceability ───────────────────────
        try:
            vector_store = get_pinecone_store()
            if all_snippets:
                research_docs = all_snippets[:100]  # Cap storage
                ids = [f"research_{analysis_id}_{i}" for i in range(len(research_docs))]
                metadatas = [
                    {"analysis_id": analysis_id, "type": "research", "index": i}
                    for i in range(len(research_docs))
                ]
                vector_store.add_documents(
                    documents=research_docs,
                    metadatas=metadatas,
                    ids=ids,
                    analysis_id=analysis_id,
                )
                logger.info(f"Stored {len(research_docs)} research snippets in Pinecone")
        except Exception as e:
            logger.warning(f"Pinecone storage failed (non-critical): {e}")

        # ── Step 3b: Early Keyword Detection (Resilience) ────────────────────
        litigation_keywords = [
            "litigation", "case", "court", "nclt", "dispute",
            "fraud", "penalty", "sebi", "rbi penalty", "defaulter", "debarment"
        ]
        litigation_count = 0
        regulatory_signals = []
        
        # Scan ALL snippets (from both Serp and GNews) for maximum resilience
        for snippet in all_snippets:
            snippet_low = snippet.lower()
            if any(kw in snippet_low for kw in litigation_keywords):
                litigation_count += 1
                if "rbi" in snippet_low:
                    regulatory_signals.append("RBI Regulatory Action")
                if "sebi" in snippet_low:
                    regulatory_signals.append("SEBI Compliance Signal")
        
        # Sync with financial metrics EARLY
        fin_metrics = state.get("financial_metrics")
        if fin_metrics:
            # Note: fin_metrics might be a dict or a Pydantic model depending on where it came from
            if isinstance(fin_metrics, dict):
                current_fin_lit = fin_metrics.get("litigation_mentions", 0)
                if litigation_count > current_fin_lit:
                    logger.info(f"Early Sync: Research ({litigation_count}) > Financial ({current_fin_lit})")
                    fin_metrics["litigation_mentions"] = litigation_count
            else:
                # Assuming it's the Pydantic model
                if litigation_count > fin_metrics.litigation_mentions:
                    logger.info(f"Early Sync: Research ({litigation_count}) > Financial ({fin_metrics.litigation_mentions})")
                    fin_metrics.litigation_mentions = litigation_count

        # ── Step 4: LLM Signal Extraction ────────────────────────────────────
        signal_result = await extract_signals(all_snippets, company_name, sector)
        risk_signals = signal_result["signals"]
        positive_highlights = signal_result["positive_highlights"]
        negative_highlights = signal_result["negative_highlights"]

        logger.info(
            f"Signals: {len(risk_signals)} risk, "
            f"{len(positive_highlights)} positive, "
            f"{len(negative_highlights)} negative"
        )

        # ── Step 4b: Fallback Highlights (Resilience) ────────────────────────
        # If AI found nothing but keywords exist, or AI failed (429), inject fallbacks
        if not negative_highlights and (litigation_count > 0 or regulatory_signals):
            logger.warning("AI signal extraction returned empty; using local fallback highlights")
            if litigation_count > 0:
                negative_highlights.append(f"System detected {litigation_count} potential litigation/regulatory mentions in research snippets.")
            
            for reg in sorted(list(set(regulatory_signals))):
                negative_highlights.append(f"Detected potential regulatory flag: {reg}")

        # ── Step 5: Promoter Intelligence ────────────────────────────────────
        promoter_profile = await analyze_promoter(promoter_snippets, company_name)
        
        # Explicitly merge promoter controversies into negative highlights for visibility
        if promoter_profile.controversies:
            for controversy in promoter_profile.controversies:
                if controversy not in negative_highlights:
                    logger.info(f"Merging promoter controversy to negative news: {controversy[:50]}...")
                    negative_highlights.insert(0, controversy)  # Insert at top for visibility

        # ── Step 6: Sector Intelligence ──────────────────────────────────────
        sector_intelligence = await analyze_sector(sector_snippets, sector)

        # ── Step 7: Compute Research Score ───────────────────────────────────
        research_score = compute_research_score(
            signals=risk_signals,
            promoter_score=promoter_profile.promoter_reputation_score,
            sector_outlook=sector_intelligence.sector_outlook,
        )

        # ── Step 8: Final Sync (already handled early, but ensure model sync) ─
        # This step is preserved for final count consistency

        # ── Step 9: Build backward-compatible ResearchSignals ────────────────
        research_signals = ResearchSignals(
            promoter_risk=promoter_profile.risk_level
                if promoter_profile.risk_level != "unknown"
                else ("high" if promoter_profile.promoter_reputation_score < 40
                      else "medium" if promoter_profile.promoter_reputation_score < 70
                      else "low"),
            sector_risk=sector_intelligence.regulatory_risk,
            litigation_count=litigation_count,
            negative_news=negative_highlights[:10],
            positive_news=positive_highlights[:10],
            promoter_background=promoter_profile.summary,
            industry_outlook=sector_intelligence.summary,
            regulatory_changes=(
                ", ".join(sector_intelligence.industry_headwinds[:3])
                if sector_intelligence.industry_headwinds
                else None
            ),
            sources=unique_sources[:50],
            research_score=research_score,
            articles_analyzed=article_count,
            sources_used=len(unique_sources),
        )

        logger.info(
            f"Research complete: score={research_score}, "
            f"promoter_risk={research_signals.promoter_risk}, "
            f"sector_risk={research_signals.sector_risk}, "
            f"litigation={litigation_count}, snippets={article_count}"
        )

        # ── Step 10: Build full ResearchReport model ────────────────────────
        full_report = ResearchReport(
            promoter_profile=promoter_profile,
            sector_intelligence=sector_intelligence,
            risk_signals=risk_signals,
            positive_signals=positive_highlights,
            negative_signals=negative_highlights,
            research_score=research_score,
            sources=unique_sources,
            articles_analyzed=article_count,
            sources_used=len(unique_sources)
        )

        # ── Step 11: Cache results ───────────────────────────────────────────
        signals_dict = research_signals.model_dump()
        cache.set_cached(company_name, signals_dict)

    except Exception as e:
        error_msg = f"Research agent error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)

        # Fallback — return minimal signals
        research_signals = ResearchSignals(
            promoter_risk="unknown",
            sector_risk="unknown",
            research_score=50.0,
        )
        full_report = ResearchReport(research_score=50.0)

    logger.info("RESEARCH AGENT v2: Pipeline complete")

    return {
        **state,
        "research_signals": research_signals.model_dump(),
        "research_report": full_report.model_dump(),
        "status": AnalysisStatus.RESEARCHING.value,
        "current_agent": "research_agent",
        "errors": errors,
    }
