"""
Result caching for Intelli-Credit.
Hash-based caching of expensive agent outputs with TTL expiration.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class ResultCache:
    """
    File-based result cache using deterministic input hashing.

    Cache key = SHA256(company_name + sector + doc_content_hash)
    Stored as JSON in CACHE_DIR with TTL expiration.
    """

    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: Optional[int] = None):
        settings = get_settings()
        self.cache_dir = Path(cache_dir or getattr(settings, "CACHE_DIR", "./cache"))
        self.ttl_seconds = (ttl_hours or getattr(settings, "CACHE_TTL_HOURS", 24)) * 3600
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, **kwargs) -> str:
        """Generate deterministic cache key from keyword arguments."""
        serialized = json.dumps(kwargs, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:24]

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if valid. Returns None on miss."""
        key = self._make_key(**kwargs)
        path = self._cache_path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = data.get("_cached_at", 0)

            if time.time() - cached_at > self.ttl_seconds:
                logger.info(f"Cache expired for key {key}")
                path.unlink(missing_ok=True)
                return None

            logger.info(f"Cache HIT for key {key}")
            return data.get("result")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Corrupt cache entry {key}: {e}")
            path.unlink(missing_ok=True)
            return None

    def set(self, result: Dict[str, Any], **kwargs) -> str:
        """Store result in cache. Returns the cache key."""
        key = self._make_key(**kwargs)
        path = self._cache_path(key)

        data = {
            "_cached_at": time.time(),
            "_key_params": kwargs,
            "result": result,
        }

        path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Cache SET for key {key}")
        return key

    def invalidate(self, **kwargs) -> bool:
        """Remove a specific cached result. Returns True if deleted."""
        key = self._make_key(**kwargs)
        path = self._cache_path(key)
        if path.exists():
            path.unlink()
            logger.info(f"Cache INVALIDATED for key {key}")
            return True
        return False

    def clear_all(self) -> int:
        """Clear all cached results. Returns count of deleted entries."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        logger.info(f"Cache CLEARED: {count} entries removed")
        return count


# ─── Singleton ────────────────────────────────────────────────────────────────

_cache: Optional[ResultCache] = None


def get_result_cache() -> ResultCache:
    """Get or create the result cache singleton."""
    global _cache
    if _cache is None:
        _cache = ResultCache()
    return _cache
