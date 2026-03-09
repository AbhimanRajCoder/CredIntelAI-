"""
Intelli-Credit: Supabase Repository Module.
Provides CRUD operations for analyses, documents, and reports tables,
plus Supabase Storage upload for PDF files.
"""

import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseRepository:
    """
    Repository for Supabase database and storage operations.

    All public methods are async-safe. The Supabase Python SDK is synchronous,
    so blocking calls are dispatched via asyncio.to_thread for non-blocking behavior.
    """

    def __init__(self):
        self.client = get_supabase_client()
        self.settings = get_settings()

    @property
    def is_available(self) -> bool:
        """Check if Supabase client is connected."""
        return self.client is not None

    # ─── Analyses ────────────────────────────────────────────────────────────

    async def create_analysis(
        self,
        analysis_id: str,
        company_name: str,
        sector: str = "",
        user_id: Optional[str] = None,
        status: str = "queued",
        loan_amount_requested: Optional[float] = None,
        due_diligence_notes: str = "",
    ) -> bool:
        """Create a new analysis record in Supabase."""
        if not self.is_available:
            return False

        data = {
            "id": analysis_id,
            "company_name": company_name,
            "sector": sector,
            "status": status,
            "loan_amount_requested": loan_amount_requested,
            "due_diligence_notes": due_diligence_notes,
        }
        if user_id:
            data["user_id"] = user_id

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("analyses").insert(data).execute()
            )
            logger.info(f"Created analysis record: {analysis_id}")
            return True if result.data else False
        except Exception as e:
            logger.error(f"Failed to create analysis: {e}")
            return False

    async def update_analysis_status(
        self, analysis_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        """Update the status of an analysis."""
        if not self.is_available:
            return None

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("analyses")
                .update({"status": status})
                .eq("id", analysis_id)
                .execute()
            )
            logger.debug(f"Updated analysis {analysis_id} status → {status}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update analysis status: {e}")
            return None

    async def update_analysis_results(
        self,
        analysis_id: str,
        company_name: Optional[str] = None,
        sector: Optional[str] = None,
        risk_score: Optional[float] = None,
        credit_grade: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update analysis with company details, risk results, and/or status."""
        if not self.is_available:
            return None

        update_data: Dict[str, Any] = {}
        if company_name is not None:
            update_data["company_name"] = company_name
        if sector is not None:
            update_data["sector"] = sector
        if risk_score is not None:
            update_data["risk_score"] = risk_score
        if credit_grade is not None:
            update_data["credit_grade"] = credit_grade
        if status is not None:
            update_data["status"] = status

        if not update_data:
            return None

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("analyses")
                .update(update_data)
                .eq("id", analysis_id)
                .execute()
            )
            logger.info(f"Updated analysis results for {analysis_id}: {update_data}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update analysis results: {e}")
            return None

    async def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single analysis by ID."""
        if not self.is_available:
            return None

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("analyses")
                .select("*")
                .eq("id", analysis_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Failed to fetch analysis {analysis_id}: {e}")
            return None

    async def list_analyses(self, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent analyses from Supabase."""
        if not self.is_available:
            return []

        try:
            query = self.client.table("analyses").select("*").order("created_at", desc=True).limit(limit)
            
            if user_id:
                query = query.eq("user_id", user_id)
                
            response = await asyncio.to_thread(query.execute)
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to list analyses: {e}")
            return []

    # ─── Documents ───────────────────────────────────────────────────────────

    async def create_document(
        self,
        analysis_id: str,
        file_name: str,
        file_path: str,
        storage_path: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Insert document metadata record."""
        if not self.is_available:
            return None

        data = {
            "analysis_id": analysis_id,
            "file_name": file_name,
            "file_path": file_path,
            "storage_path": storage_path,
            "file_size": file_size,
        }

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("documents").insert(data).execute()
            )
            logger.info(f"Created document record: {file_name} for analysis {analysis_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create document record: {e}")
            return None

    async def get_documents_for_analysis(
        self, analysis_id: str
    ) -> List[Dict[str, Any]]:
        """List all documents for a given analysis."""
        if not self.is_available:
            return []

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("documents")
                .select("*")
                .eq("analysis_id", analysis_id)
                .order("created_at")
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get documents for analysis {analysis_id}: {e}")
            return []

    # ─── Reports ─────────────────────────────────────────────────────────────

    async def create_report(
        self,
        analysis_id: str,
        json_report: Optional[Dict[str, Any]] = None,
        docx_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Insert or upsert a report record for an analysis."""
        if not self.is_available:
            return None

        data = {
            "analysis_id": analysis_id,
            "json_report": json_report,
            "docx_path": docx_path,
            "pdf_path": pdf_path,
        }

        try:
            # Check if report already exists for this analysis
            existing = await asyncio.to_thread(
                lambda: self.client.table("reports")
                .select("id")
                .eq("analysis_id", analysis_id)
                .execute()
            )

            if existing.data:
                # Update existing report
                # We try one more time without pdf_path if it fails
                try:
                    result = await asyncio.to_thread(
                        lambda: self.client.table("reports")
                        .update({
                            "json_report": json_report, 
                            "docx_path": docx_path,
                            "pdf_path": pdf_path
                        })
                        .eq("analysis_id", analysis_id)
                        .execute()
                    )
                except Exception as e:
                    if "pdf_path" in str(e):
                        logger.warning("Supabase 'reports' table missing 'pdf_path' column. Saving PDF path to 'docx_path' as fallback.")
                        result = await asyncio.to_thread(
                            lambda: self.client.table("reports")
                            .update({
                                "json_report": json_report, 
                                "docx_path": pdf_path # Fallback
                            })
                            .eq("analysis_id", analysis_id)
                            .execute()
                        )
                    else:
                        raise e
            else:
                # Insert new report
                try:
                    result = await asyncio.to_thread(
                        lambda: self.client.table("reports").insert(data).execute()
                    )
                except Exception as e:
                    if "pdf_path" in str(e):
                        logger.warning("Supabase 'reports' table missing 'pdf_path' column. Saving PDF path to 'docx_path' as fallback.")
                        fallback_data = {
                            "analysis_id": analysis_id,
                            "json_report": json_report,
                            "docx_path": pdf_path, # Fallback
                        }
                        result = await asyncio.to_thread(
                            lambda: self.client.table("reports").insert(fallback_data).execute()
                        )
                    else:
                        raise e

            logger.info(f"Saved report for analysis {analysis_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return None

    async def get_report(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Fetch report by analysis_id."""
        if not self.is_available:
            return None

        try:
            result = await asyncio.to_thread(
                lambda: self.client.table("reports")
                .select("*")
                .eq("analysis_id", analysis_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to fetch report for {analysis_id}: {e}")
            return None

    # ─── Supabase Storage ────────────────────────────────────────────────────

    async def upload_file_to_storage(
        self,
        analysis_id: str,
        file_name: str,
        file_content: bytes,
    ) -> Optional[str]:
        """
        Upload a file to Supabase Storage.

        Stores at: documents/{analysis_id}/{file_name}
        Returns the storage path on success, None on failure.
        """
        if not self.is_available:
            return None

        bucket_name = self.settings.SUPABASE_STORAGE_BUCKET
        storage_path = f"{analysis_id}/{file_name}"

        try:
            await asyncio.to_thread(
                lambda: self.client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=file_content,
                    file_options={"content-type": "application/pdf"},
                )
            )
            logger.info(f"Uploaded {file_name} to Supabase Storage: {storage_path}")
            return storage_path
        except Exception as e:
            # If file already exists, log warning but don't fail
            error_msg = str(e)
            if "Duplicate" in error_msg or "already exists" in error_msg:
                logger.warning(f"File already exists in storage: {storage_path}")
                return storage_path
            logger.error(f"Failed to upload to Supabase Storage: {e}")
            return None


# ─── Singleton ───────────────────────────────────────────────────────────────

_repository: Optional[SupabaseRepository] = None


def get_supabase_repository() -> SupabaseRepository:
    """Get or create the SupabaseRepository singleton."""
    global _repository
    if _repository is None:
        _repository = SupabaseRepository()
    return _repository
