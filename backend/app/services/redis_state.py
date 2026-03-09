"""
Intelli-Credit: Redis State Management Service.
Replaces in-memory dictionaries with a shared Redis cache so that
analysis status, results, and metrics are consistent across
multiple Gunicorn/Uvicorn workers and even across multiple servers.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

# ─── Key Schema ───────────────────────────────────────────────────────────────
# analysis:{id}:status   → str  (e.g. "processing")
# analysis:{id}:result   → JSON (full workflow result dict)
# analysis:{id}:docs     → JSON (list of document file paths)
# analysis:{id}:progress → JSON (progress payload for SSE/polling)

_KEY_STATUS = "analysis:{analysis_id}:status"
_KEY_RESULT = "analysis:{analysis_id}:result"
_KEY_DOCS = "analysis:{analysis_id}:docs"
_KEY_PROGRESS = "analysis:{analysis_id}:progress"


class RedisStateService:
    """
    Centralised Redis-backed state store for credit-appraisal analyses.

    All public methods are async. Redis operations use redis.asyncio for
    non-blocking I/O inside the FastAPI event loop.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._url = settings.REDIS_URL
        self._state_ttl = settings.REDIS_STATE_TTL_HOURS * 3600
        self._result_ttl = settings.REDIS_RESULT_TTL_HOURS * 3600
        self._pool: Optional[aioredis.Redis] = None

    # ─── Connection ───────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Initialise the async Redis connection pool."""
        if self._pool is None:
            self._pool = aioredis.from_url(
                self._url,
                decode_responses=True,
                max_connections=20,
            )
            # Verify connectivity
            await self._pool.ping()
            logger.info(f"Redis connected: {self._url}")

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self._pool:
            await self._pool.aclose()
            self._pool = None
            logger.info("Redis connection closed")

    @property
    def pool(self) -> aioredis.Redis:
        if self._pool is None:
            raise RuntimeError(
                "Redis not connected. Call 'await redis_state.connect()' "
                "during application startup."
            )
        return self._pool

    # ─── Status ───────────────────────────────────────────────────────────────

    async def set_status(self, analysis_id: str, status: str) -> None:
        key = _KEY_STATUS.format(analysis_id=analysis_id)
        await self.pool.set(key, status, ex=self._state_ttl)

    async def get_status(self, analysis_id: str) -> Optional[str]:
        key = _KEY_STATUS.format(analysis_id=analysis_id)
        return await self.pool.get(key)

    # ─── Full Result ──────────────────────────────────────────────────────────

    async def set_result(self, analysis_id: str, result: Dict[str, Any]) -> None:
        key = _KEY_RESULT.format(analysis_id=analysis_id)
        await self.pool.set(key, json.dumps(result, default=str), ex=self._result_ttl)

    async def get_result(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        key = _KEY_RESULT.format(analysis_id=analysis_id)
        raw = await self.pool.get(key)
        if raw:
            return json.loads(raw)
        return None

    # ─── Document Paths ───────────────────────────────────────────────────────

    async def add_documents(self, analysis_id: str, paths: List[str]) -> None:
        key = _KEY_DOCS.format(analysis_id=analysis_id)
        existing_raw = await self.pool.get(key)
        existing = json.loads(existing_raw) if existing_raw else []
        existing.extend(paths)
        await self.pool.set(key, json.dumps(existing), ex=self._state_ttl)

    async def get_documents(self, analysis_id: str) -> List[str]:
        key = _KEY_DOCS.format(analysis_id=analysis_id)
        raw = await self.pool.get(key)
        return json.loads(raw) if raw else []

    # ─── Progress (for SSE / polling) ─────────────────────────────────────────

    async def set_progress(self, analysis_id: str, progress: Dict[str, Any]) -> None:
        key = _KEY_PROGRESS.format(analysis_id=analysis_id)
        await self.pool.set(key, json.dumps(progress, default=str), ex=self._state_ttl)

    async def get_progress(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        key = _KEY_PROGRESS.format(analysis_id=analysis_id)
        raw = await self.pool.get(key)
        if raw:
            return json.loads(raw)
        return None

    # ─── Bulk Listing ─────────────────────────────────────────────────────────

    async def list_analysis_ids(self) -> List[str]:
        """Return all known analysis IDs by scanning status keys."""
        keys = []
        async for key in self.pool.scan_iter(match="analysis:*:status", count=100):
            # analysis:{uuid}:status → extract uuid
            parts = key.split(":")
            if len(parts) == 3:
                keys.append(parts[1])
        return keys

    # ─── Cleanup ──────────────────────────────────────────────────────────────

    async def delete_analysis(self, analysis_id: str) -> None:
        """Remove all Redis keys for an analysis (e.g. after TTL or manual cleanup)."""
        keys = [
            _KEY_STATUS.format(analysis_id=analysis_id),
            _KEY_RESULT.format(analysis_id=analysis_id),
            _KEY_DOCS.format(analysis_id=analysis_id),
            _KEY_PROGRESS.format(analysis_id=analysis_id),
        ]
        await self.pool.delete(*keys)


# ─── Singleton ────────────────────────────────────────────────────────────────

_redis_state: Optional[RedisStateService] = None


def get_redis_state() -> RedisStateService:
    """Get or create the RedisStateService singleton."""
    global _redis_state
    if _redis_state is None:
        _redis_state = RedisStateService()
    return _redis_state
