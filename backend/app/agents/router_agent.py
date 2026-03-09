"""
Router Agent for Intelli-Credit.
Orchestrates the workflow by validating inputs and directing task flow.
"""

import logging
from typing import Dict, Any

from app.models.schemas import AnalysisStatus

logger = logging.getLogger(__name__)


async def router_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Router Agent: Validates inputs and determines workflow routing.

    Inputs:
        - company_name
        - document_paths
        - due_diligence_notes

    Outputs:
        - Updated state with routing directives and validation status
    """
    logger.info("=" * 60)
    logger.info("ROUTER AGENT: Starting workflow orchestration")
    logger.info("=" * 60)

    company_name = state.get("company_name", "")
    sector = state.get("sector", "")
    document_paths = state.get("document_paths", [])
    due_diligence_notes = state.get("due_diligence_notes", "")

    errors = state.get("errors", [])

    # ── Validate inputs ──────────────────────────────────────────────────────
    if not company_name:
        errors.append("Company name is required")
    if not sector:
        errors.append("Sector is required")

    if errors:
        logger.error(f"Router Agent validation failed: {errors}")
        return {
            **state,
            "status": AnalysisStatus.FAILED.value,
            "errors": errors,
            "current_agent": "router_agent",
        }

    # ── Log workflow configuration ───────────────────────────────────────────
    logger.info(f"Company: {company_name}")
    logger.info(f"Sector: {sector}")
    logger.info(f"Documents: {len(document_paths)} files")
    logger.info(f"Due Diligence Notes: {'Provided' if due_diligence_notes else 'None'}")

    has_documents = len(document_paths) > 0

    logger.info(f"Workflow path: {'Full pipeline' if has_documents else 'Research-only pipeline'}")
    logger.info("Router Agent: Routing to Data Ingestor Agent")

    return {
        **state,
        "status": AnalysisStatus.PROCESSING.value,
        "current_agent": "router_agent",
        "has_documents": has_documents,
    }
