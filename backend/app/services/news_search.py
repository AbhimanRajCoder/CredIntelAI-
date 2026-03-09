"""
GNews API Integration for Intelli-Credit.
Provides structured news article retrieval. Falls back gracefully if no API key.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class GNewsService:
    """Structured news search via GNews API."""

    BASE_URL = "https://gnews.io/api/v4/search"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.GNEWS_API_KEY
        self.enabled = bool(self.api_key)

    async def search_news(
        self,
        query: str,
        max_results: int = 5,
        lang: str = "en",
        country: str = "in",
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles via GNews.

        Returns list of dicts with: title, description, url, published_at, source_name
        """
        if not self.enabled:
            logger.debug("GNews API key not configured — skipping news search")
            return []

        params = {
            "q": query,
            "token": self.api_key,
            "lang": lang,
            "country": country,
            "max": min(max_results, 10),
            "sortby": "relevance",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            articles = []
            for item in data.get("articles", []):
                articles.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("publishedAt", ""),
                    "source_name": item.get("source", {}).get("name", ""),
                })

            logger.info(f"GNews search '{query}': {len(articles)} articles")
            return articles

        except httpx.HTTPStatusError as e:
            logger.warning(f"GNews HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.warning(f"GNews search error: {str(e)}")
            return []

    async def search_batch(
        self, queries: List[str], max_per_query: int = 5
    ) -> List[Dict[str, Any]]:
        """Run multiple queries and return deduplicated articles."""
        seen_urls = set()
        all_articles = []

        for query in queries:
            results = await self.search_news(query, max_results=max_per_query)
            for article in results:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(article)

        return all_articles


# Singleton
_gnews_service: Optional[GNewsService] = None


def get_gnews_service() -> GNewsService:
    """Get or create the GNews service singleton."""
    global _gnews_service
    if _gnews_service is None:
        _gnews_service = GNewsService()
    return _gnews_service
