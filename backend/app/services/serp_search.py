"""
SerpAPI Search Service for Intelli-Credit.
Performs web research about companies and promoters.
"""

import logging
from typing import List, Dict, Any, Optional

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class SerpSearchService:
    """Web search service using SerpAPI for company research."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.SERP_API_KEY

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Perform a web search using SerpAPI."""
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": num_results,
            "gl": "in",  # India
            "hl": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("organic_results", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })

            logger.info(f"SerpAPI search for '{query}': {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"SerpAPI HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"SerpAPI search error: {str(e)}")
            return []

    async def research_company(self, company_name: str, sector: str) -> Dict[str, Any]:
        """
        Perform comprehensive company research with multiple queries.
        Returns aggregated research data.
        """
        queries = [
            f"{company_name} litigation India",
            f"{company_name} promoter background",
            f"{sector} industry outlook India",
            f"{company_name} financial news",
            f"{company_name} regulatory compliance India",
        ]

        all_results: Dict[str, List[Dict[str, Any]]] = {}
        all_snippets: List[str] = []
        all_sources: List[str] = []

        for query in queries:
            results = await self.search(query)
            all_results[query] = results
            for r in results:
                if r.get("snippet"):
                    all_snippets.append(r["snippet"])
                if r.get("link"):
                    all_sources.append(r["link"])

        # Categorize results
        litigation_results = all_results.get(queries[0], [])
        promoter_results = all_results.get(queries[1], [])
        industry_results = all_results.get(queries[2], [])
        news_results = all_results.get(queries[3], [])

        # Count litigation mentions
        litigation_count = 0
        litigation_keywords = ["litigation", "case", "court", "nclt", "dispute", "fraud", "penalty"]
        for r in litigation_results:
            snippet_lower = r.get("snippet", "").lower()
            if any(kw in snippet_lower for kw in litigation_keywords):
                litigation_count += 1

        # Identify negative news
        negative_keywords = ["fraud", "default", "scam", "loss", "penalty", "violation", "ban", "arrest"]
        negative_news = []
        for r in news_results:
            snippet_lower = r.get("snippet", "").lower()
            if any(kw in snippet_lower for kw in negative_keywords):
                negative_news.append(r.get("snippet", ""))

        return {
            "all_snippets": all_snippets,
            "sources": list(set(all_sources)),
            "litigation_count": litigation_count,
            "negative_news": negative_news,
            "promoter_snippets": [r.get("snippet", "") for r in promoter_results],
            "industry_snippets": [r.get("snippet", "") for r in industry_results],
            "news_snippets": [r.get("snippet", "") for r in news_results],
        }


# Singleton
_serp_service: Optional[SerpSearchService] = None


def get_serp_service() -> SerpSearchService:
    """Get or create the SerpAPI service singleton."""
    global _serp_service
    if _serp_service is None:
        _serp_service = SerpSearchService()
    return _serp_service
