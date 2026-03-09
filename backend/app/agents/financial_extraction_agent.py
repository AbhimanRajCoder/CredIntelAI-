"""
Financial Extraction Agent for Intelli-Credit.
Dedicated agent that converts extracted tables and text into structured
financial metrics using deterministic parsing with LLM fallback.
"""

import json
import logging
from typing import Any, Dict, List

from app.models.schemas import FinancialMetrics, AnalysisStatus
from app.models.state import add_reasoning_step
from app.services.table_to_metrics import (
    tables_to_metrics,
    compute_derived_metrics,
    get_latest_year_metrics,
)
from app.services.groq_client import get_groq_client
from app.utils.normalizer import normalize_indian_amount
from app.utils.prompts import FINANCIAL_EXTRACTION_PROMPT
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)


@track_agent(timeout=45)
async def financial_extraction_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Financial Extraction Agent: Extract structured financial metrics.

    Pipeline:
        1. Parse reconstructed tables → deterministic metrics (table_to_metrics)
        2. Compute derived ratios (D/E, ICR, etc.)
        3. Fall back to LLM extraction for missing metrics
        4. Normalize all values (Indian units)
        5. Output ExtractedFinancials to state

    This agent replaces the LLM-only extraction in the old data_ingestor.
    """
    logger.info("FINANCIAL EXTRACTION AGENT: Starting structured extraction")

    extracted_text = state.get("extracted_text", "")
    tables = state.get("reconstructed_tables", [])
    errors = list(state.get("errors", []))

    metrics_by_year: Dict[str, Dict[str, Any]] = {}
    extraction_method = "unknown"
    fiscal_years_found: List[str] = []

    # ── Step 1: Deterministic table-based extraction ────────────────────────
    if tables:
        try:
            metrics_by_year = tables_to_metrics(tables)
            if metrics_by_year:
                extraction_method = "table_parser"
                fiscal_years_found = sorted(metrics_by_year.keys())
                logger.info(
                    f"Table extraction: {len(metrics_by_year)} fiscal years — "
                    f"{fiscal_years_found}"
                )

                # Compute derived ratios for each year
                for year in metrics_by_year:
                    metrics_by_year[year] = compute_derived_metrics(metrics_by_year[year])

        except Exception as e:
            logger.warning(f"Table-based extraction failed: {e}")
            errors.append(f"Table extraction error: {str(e)}")

    # ── Step 2: LLM fallback for missing metrics ───────────────────────────
    latest_year, latest_metrics = get_latest_year_metrics(metrics_by_year)
    critical_fields = ["revenue", "profit", "debt"]
    missing_fields = [f for f in critical_fields if f not in latest_metrics]

    if missing_fields or not latest_metrics:
        logger.info(
            f"Missing critical fields: {missing_fields or 'all'}. "
            f"Using LLM fallback extraction."
        )

        try:
            llm_metrics = await _llm_extract_financials(extracted_text)
            if llm_metrics:
                if extraction_method == "table_parser":
                    extraction_method = "hybrid"
                else:
                    extraction_method = "llm_fallback"

                # Merge LLM results into metrics (don't overwrite table results)
                if not latest_year:
                    latest_year = "FY_UNKNOWN"

                if latest_year not in metrics_by_year:
                    metrics_by_year[latest_year] = {}

                for key, value in llm_metrics.items():
                    if key not in metrics_by_year[latest_year]:
                        metrics_by_year[latest_year][key] = value

                # Recompute derived ratios
                metrics_by_year[latest_year] = compute_derived_metrics(
                    metrics_by_year[latest_year]
                )

                fiscal_years_found = sorted(metrics_by_year.keys())

        except Exception as e:
            error_msg = f"LLM financial extraction failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    # ── Step 3: Build backwards-compatible FinancialMetrics ─────────────────
    _, latest = get_latest_year_metrics(metrics_by_year)
    financial_metrics = _build_financial_metrics(latest)

    # ── Step 4: Build ExtractedFinancials ───────────────────────────────────
    extracted_financials = {
        "metrics_by_year": metrics_by_year,
        "latest_metrics": latest,
        "detected_sections": state.get("detected_sections", []),
        "extraction_method": extraction_method,
        "fiscal_years_found": fiscal_years_found,
    }

    # ── Step 5: Reasoning trace ────────────────────────────────────────────
    metrics_summary = ", ".join(
        f"{k}={v}" for k, v in latest.items()
        if k in critical_fields and v is not None
    )
    reasoning_trace = add_reasoning_step(
        state,
        agent="financial_extraction_agent",
        decision=f"Extracted financials via {extraction_method} for {len(metrics_by_year)} years",
        evidence=metrics_summary or "No critical metrics found",
    )

    logger.info(
        f"FINANCIAL EXTRACTION AGENT: Complete — "
        f"method={extraction_method}, years={len(metrics_by_year)}, "
        f"fields={len(latest)}"
    )

    return {
        **state,
        "financial_metrics": financial_metrics.model_dump() if financial_metrics else {},
        "extracted_financials": extracted_financials,
        "status": AnalysisStatus.INGESTING.value,
        "current_agent": "financial_extraction_agent",
        "errors": errors,
        "reasoning_trace": reasoning_trace,
    }


async def _llm_extract_financials(text: str) -> Dict[str, Any]:
    """Use LLM to extract financial metrics from raw text (fallback)."""
    if not text or len(text) < 100:
        return {}

    doc_text = text[:12000]  # Truncate for context window

    groq = get_groq_client()
    prompt = FINANCIAL_EXTRACTION_PROMPT.format(document_text=doc_text)

    result = await groq.generate_json(
        prompt=prompt,
        system_message="You are an expert financial data extraction specialist. Always respond in valid JSON.",
    )

    # Normalize values
    normalized = {}
    for key, value in result.items():
        if key in ("promoter_names", "litigation_mentions"):
            normalized[key] = value
            continue

        if isinstance(value, (int, float)):
            normalized[key] = float(value)
        elif isinstance(value, str):
            parsed = normalize_indian_amount(value)
            if parsed is not None:
                normalized[key] = parsed

    return normalized


def _build_financial_metrics(metrics: Dict[str, Any]) -> FinancialMetrics:
    """Build FinancialMetrics Pydantic model from dict."""
    return FinancialMetrics(
        revenue=metrics.get("revenue"),
        profit=metrics.get("profit"),
        debt=metrics.get("debt"),
        cashflow=metrics.get("cashflow"),
        bank_loans=metrics.get("bank_loans"),
        litigation_mentions=metrics.get("litigation_mentions", 0),
        debt_to_equity_ratio=metrics.get("debt_to_equity_ratio"),
        current_ratio=metrics.get("current_ratio"),
        interest_coverage_ratio=metrics.get("interest_coverage_ratio"),
        net_profit_margin=metrics.get("net_profit_margin"),
        return_on_equity=metrics.get("return_on_equity"),
        raw_extracted_data=metrics,
    )
