"""
Intelli-Credit: Storage Service.
Encapsulates file storage logic — local temp files for processing,
Supabase Storage for persistent documents.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import get_settings
from app.db.supabase_repository import get_supabase_repository

logger = logging.getLogger(__name__)


class StorageService:
    """
    Manages document storage across local and cloud layers.

    * **Local temp**: Files are saved to a temporary directory during
      processing (OCR, parsing). These are ephemeral and cleaned up.
    * **Supabase Storage**: Persistent storage for uploaded PDFs so they
      survive worker restarts and container redeployments.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._upload_dir = Path(self.settings.UPLOAD_DIR)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    # ─── Upload & Persist ─────────────────────────────────────────────────────

    async def save_upload(
        self,
        analysis_id: str,
        file_name: str,
        file_content: bytes,
    ) -> Tuple[str, Optional[str]]:
        """
        Save an uploaded file locally and (if available) to Supabase Storage.

        Returns:
            (local_path, storage_path) — storage_path is None if Supabase
            is not configured.
        """
        # 1. Local save (needed for agent processing)
        local_dir = self._upload_dir / analysis_id
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / file_name

        local_path.write_bytes(file_content)
        logger.info(f"Saved locally: {local_path} ({len(file_content)} bytes)")

        # 2. Persistent save to Supabase Storage
        storage_path: Optional[str] = None
        repo = get_supabase_repository()
        if repo.is_available:
            storage_path = await repo.upload_file_to_storage(
                analysis_id=analysis_id,
                file_name=file_name,
                file_content=file_content,
            )

        return str(local_path), storage_path

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def get_local_paths(self, analysis_id: str) -> List[str]:
        """List all local files for an analysis."""
        local_dir = self._upload_dir / analysis_id
        if not local_dir.exists():
            return []
        return [str(p) for p in local_dir.iterdir() if p.is_file()]

    # ─── Cleanup ──────────────────────────────────────────────────────────────

    def cleanup_local(self, analysis_id: str) -> None:
        """
        Remove local temp files for a completed analysis.
        Call this after the workflow finishes and results are persisted.
        """
        local_dir = self._upload_dir / analysis_id
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)
            logger.info(f"Cleaned up local uploads for {analysis_id}")


# ─── Singleton ────────────────────────────────────────────────────────────────

_storage: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the StorageService singleton."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
