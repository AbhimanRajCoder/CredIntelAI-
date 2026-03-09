"""
Research Cache Service for Intelli-Credit.
File-based JSON cache keyed on company_name + date to reduce API costs.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.config import get_settings

logger = logging.getLogger(__name__)


class ResearchCache:
    """File-based research results cache with configurable TTL."""

    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = Path(self.settings.RESEARCH_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = self.settings.RESEARCH_CACHE_TTL_HOURS

    def _cache_key(self, company_name: str) -> str:
        """Generate a cache filename from company name + current date."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        raw = f"{company_name.strip().lower()}_{date_str}"
        hash_key = hashlib.md5(raw.encode()).hexdigest()
        return hash_key

    def _cache_path(self, company_name: str) -> Path:
        return self.cache_dir / f"{self._cache_key(company_name)}.json"

    def get_cached(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached research results if they exist and are within TTL.
        Returns None if cache miss or expired.
        """
        path = self._cache_path(company_name)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data.get("_cached_at", ""))
            if datetime.utcnow() - cached_at > timedelta(hours=self.ttl_hours):
                logger.info(f"Cache expired for '{company_name}'")
                path.unlink(missing_ok=True)
                return None

            logger.info(f"Cache HIT for '{company_name}'")
            return data.get("payload")

        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def set_cached(self, company_name: str, data: Dict[str, Any]) -> None:
        """Store research results in the cache."""
        path = self._cache_path(company_name)
        try:
            cache_entry = {
                "_cached_at": datetime.utcnow().isoformat(),
                "_company": company_name,
                "payload": data,
            }
            path.write_text(json.dumps(cache_entry, default=str), encoding="utf-8")
            logger.info(f"Cache SET for '{company_name}'")

        except Exception as e:
            logger.warning(f"Cache write error: {e}")


# Singleton
_research_cache: Optional[ResearchCache] = None


def get_research_cache() -> ResearchCache:
    """Get or create the research cache singleton."""
    global _research_cache
    if _research_cache is None:
        _research_cache = ResearchCache()
    return _research_cache
