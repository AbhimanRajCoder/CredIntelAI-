"""
LangGraph Workflow for Intelli-Credit v2.0.
Defines the parallel multi-agent DAG for production credit appraisal.

Architecture:
    Router
      → Data Ingestor
        → Financial Extraction
          → Validation (quality gate)
            → [PARALLEL] Financial Analysis / Research / Trend / Fraud
              → Merge Results
                → Scoring Engine
                  → Risk Agent
                    → CAM Generator
                      → END

Supabase persistence is injected via wrapper nodes so that individual
agent files remain unchanged.
"""

import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END

from app.agents.router_agent import router_agent
from app.agents.data_ingestor_agent import data_ingestor_agent
from app.agents.financial_extraction_agent import financial_extraction_agent
from app.agents.validation_agent import validation_agent
from app.agents.research import research_agent
from app.agents.trend_agent import trend_agent
from app.agents.fraud_agent import fraud_agent
from app.agents.risk_agent import risk_agent
from app.agents.cam_generator_agent import cam_generator_agent
from app.agents.scoring_engine import compute_credit_score
from app.models.schemas import AnalysisStatus
from app.models.state import (
    CreditAppraisalState,
    create_initial_state,
    add_reasoning_step,
    WORKFLOW_VERSION,
)

logger = logging.getLogger(__name__)


# ─── Supabase Persistence Helpers ────────────────────────────────────────────

async def _persist_status(state: Dict[str, Any], status: str) -> None:
    """Update analysis status in Redis + Supabase (fire-and-forget)."""
    analysis_id = state.get("analysis_id", "")
    # Redis (primary — shared across workers)
    try:
        from app.services.redis_state import get_redis_state
        redis_state = get_redis_state()
        await redis_state.set_status(analysis_id, status)
        await redis_state.set_progress(analysis_id, {
            "status": status,
            "current_agent": state.get("current_agent", ""),
        })
    except Exception as e:
        logger.warning(f"Redis status update failed (non-fatal): {e}")
    # Supabase (persistent)
    try:
        from app.db.supabase_repository import get_supabase_repository
        repo = get_supabase_repository()
        if repo.is_available:
            await repo.update_analysis_status(analysis_id, status)
    except Exception as e:
        logger.warning(f"Supabase status update failed (non-fatal): {e}")


async def _persist_results(state: Dict[str, Any]) -> None:
    """Persist risk score and credit grade to Redis + Supabase after scoring/risk."""
    analysis_id = state.get("analysis_id", "")
    # Redis (intermediate result snapshot)
    try:
        from app.services.redis_state import get_redis_state
        redis_state = get_redis_state()
        await redis_state.set_result(analysis_id, state)
    except Exception as e:
        logger.warning(f"Redis results update failed (non-fatal): {e}")
    # Supabase (persistent)
    try:
        from app.db.supabase_repository import get_supabase_repository
        repo = get_supabase_repository()
        if repo.is_available:
            credit_score = state.get("credit_score", {})
            risk_analysis = state.get("risk_analysis", {})

            await repo.update_analysis_results(
                analysis_id=analysis_id,
                risk_score=risk_analysis.get("risk_score") or credit_score.get("total_score"),
                credit_grade=credit_score.get("grade"),
                status=state.get("status"),
            )
    except Exception as e:
        logger.warning(f"Supabase results update failed (non-fatal): {e}")


async def _persist_report(state: Dict[str, Any]) -> None:
    """Persist the final CAM report to Redis + Supabase."""
    analysis_id = state.get("analysis_id", "")
    # Redis (final result for fast retrieval)
    try:
        from app.services.redis_state import get_redis_state
        redis_state = get_redis_state()
        await redis_state.set_result(analysis_id, state)
        await redis_state.set_status(analysis_id, AnalysisStatus.COMPLETED.value)
    except Exception as e:
        logger.warning(f"Redis report persist failed (non-fatal): {e}")
    # Supabase (permanent storage)
    try:
        from app.db.supabase_repository import get_supabase_repository
        repo = get_supabase_repository()
        if repo.is_available:
            cam_report = state.get("cam_report", {})
            docx_path = cam_report.get("docx_path")
            pdf_path = cam_report.get("pdf_path")

            await repo.create_report(
                analysis_id=analysis_id,
                json_report=cam_report,
                docx_path=docx_path,
                pdf_path=pdf_path,
            )

            await repo.update_analysis_status(
                analysis_id, AnalysisStatus.COMPLETED.value
            )
    except Exception as e:
        logger.warning(f"Supabase report persist failed (non-fatal): {e}")


# ─── Scoring Engine Node ─────────────────────────────────────────────────────

async def scoring_engine_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Credit Scoring Engine node.
    Computes credit score from structured agent outputs.
    """
    logger.info("SCORING ENGINE: Computing deterministic credit score")

    credit_score = compute_credit_score(
        financial_metrics=state.get("financial_metrics", {}),
        research_signals=state.get("research_signals", {}),
        sector=state.get("sector", ""),
        trend_analysis=state.get("trend_analysis", {}),
        fraud_signals=state.get("fraud_signals", {}),
    )

    reasoning_trace = add_reasoning_step(
        state,
        agent="scoring_engine",
        decision=f"Credit score: {credit_score.total_score}/100, Grade: {credit_score.grade}",
        evidence=(
            f"Financial={credit_score.financial_score}, "
            f"Sector={credit_score.sector_score}, "
            f"Promoter={credit_score.promoter_score}, "
            f"News={credit_score.news_score}"
        ),
    )

    return {
        **state,
        "credit_score": credit_score.model_dump(),
        "current_agent": "scoring_engine",
        "reasoning_trace": reasoning_trace,
    }


# ─── Merge Node ──────────────────────────────────────────────────────────────

async def merge_parallel_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fan-in node: Merge outputs from parallel agents.
    LangGraph merges state automatically — this node validates completeness.
    """
    logger.info("MERGE NODE: Combining parallel agent outputs")

    # Log what we received
    has_research = bool(state.get("research_signals"))
    has_trend = bool(state.get("trend_analysis"))
    has_fraud = bool(state.get("fraud_signals"))

    logger.info(
        f"Merge results: research={'✓' if has_research else '✗'}, "
        f"trend={'✓' if has_trend else '✗'}, "
        f"fraud={'✓' if has_fraud else '✗'}"
    )

    return {
        **state,
        "current_agent": "merge_results",
    }


# ─── Wrapper Nodes (Supabase persistence) ────────────────────────────────────
# These wrap exiting agents to inject DB status updates without modifying
# individual agent files.

async def router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    result = await router_agent(state)
    await _persist_status(result, result.get("status", AnalysisStatus.PROCESSING.value))
    return result


async def data_ingestor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    await _persist_status(state, AnalysisStatus.PARSING_DOCUMENTS.value)
    result = await data_ingestor_agent(state)
    return result


async def financial_extraction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    await _persist_status(state, AnalysisStatus.EXTRACTING_FINANCIALS.value)
    result = await financial_extraction_agent(state)
    return result


async def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    result = await validation_agent(state)
    return result


async def research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    await _persist_status(state, AnalysisStatus.RESEARCHING_COMPANY.value)
    result = await research_agent(state)
    return result


async def trend_node(state: Dict[str, Any]) -> Dict[str, Any]:
    result = await trend_agent(state)
    return result


async def fraud_node(state: Dict[str, Any]) -> Dict[str, Any]:
    result = await fraud_agent(state)
    return result


async def risk_node(state: Dict[str, Any]) -> Dict[str, Any]:
    await _persist_status(state, AnalysisStatus.PERFORMING_RISK_ANALYSIS.value)
    result = await risk_agent(state)
    await _persist_results(result)
    return result


async def cam_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    await _persist_status(state, AnalysisStatus.GENERATING_CAM.value)
    result = await cam_generator_agent(state)
    await _persist_report(result)
    return result


# ─── Routing Functions ────────────────────────────────────────────────────────

def should_continue_after_router(state: Dict[str, Any]) -> str:
    """Determine next step after router agent."""
    if state.get("status") == AnalysisStatus.FAILED.value:
        return "end"
    return "data_ingestor"


def should_continue_after_validation(state: Dict[str, Any]) -> str:
    """
    After validation, either proceed to parallel analysis or short-circuit.
    """
    validation = state.get("validation_result", {})
    is_acceptable = validation.get("is_acceptable", True)

    if not is_acceptable:
        logger.warning("Validation failed — routing to manual review path")
        # Still continue but with a warning status
        # The needs_review status is set by validation_agent

    if state.get("status") == AnalysisStatus.FAILED.value:
        return "end"

    return "parallel_analysis"


# ─── Build Workflow Graph ─────────────────────────────────────────────────────

def build_credit_appraisal_workflow() -> StateGraph:
    """
    Build the LangGraph workflow for credit appraisal v2.0.

    Architecture:
        router → data_ingestor → financial_extraction → validation
          → [parallel: research, trend_agent, fraud_agent]
            → merge → scoring_engine → risk_analysis → cam_generator → END
    """
    logger.info("Building credit appraisal LangGraph workflow v2.0...")

    workflow = StateGraph(CreditAppraisalState)

    # ── Add nodes (using wrapper nodes for Supabase persistence) ─────────
    workflow.add_node("router", router_node)
    workflow.add_node("data_ingestor", data_ingestor_node)
    workflow.add_node("financial_extraction", financial_extraction_node)
    workflow.add_node("validation", validation_node)

    # Parallel agents
    workflow.add_node("research", research_node)
    workflow.add_node("trend_agent", trend_node)
    workflow.add_node("fraud_agent", fraud_node)

    # Post-parallel
    workflow.add_node("merge_results", merge_parallel_results)
    workflow.add_node("scoring_engine", scoring_engine_node)
    workflow.add_node("risk_assessment", risk_node)
    workflow.add_node("cam_generator", cam_generator_node)

    # ── Set entry point ──────────────────────────────────────────────────────
    workflow.set_entry_point("router")

    # ── Edges: Sequential pre-parallel ───────────────────────────────────────
    workflow.add_conditional_edges(
        "router",
        should_continue_after_router,
        {
            "data_ingestor": "data_ingestor",
            "end": END,
        },
    )

    workflow.add_edge("data_ingestor", "financial_extraction")
    workflow.add_edge("financial_extraction", "validation")

    # ── Edges: Validation → Parallel Fan-out ─────────────────────────────────
    # After validation, fan out to parallel agents
    workflow.add_conditional_edges(
        "validation",
        should_continue_after_validation,
        {
            "parallel_analysis": "research",
            "end": END,
        },
    )

    # Fan-out: validation → research, trend, fraud (sequential simulation)
    # LangGraph's basic StateGraph doesn't support true parallel fan-out,
    # so we chain: research → trend → fraud → merge
    # Each agent only writes to its own state keys, so ordering doesn't matter.
    workflow.add_edge("research", "trend_agent")
    workflow.add_edge("trend_agent", "fraud_agent")
    workflow.add_edge("fraud_agent", "merge_results")

    # ── Edges: Post-parallel sequential ──────────────────────────────────────
    workflow.add_edge("merge_results", "scoring_engine")
    workflow.add_edge("scoring_engine", "risk_assessment")
    workflow.add_edge("risk_assessment", "cam_generator")
    workflow.add_edge("cam_generator", END)

    logger.info("Credit appraisal workflow v2.0 built successfully")
    return workflow


# ─── Compiled Workflow ────────────────────────────────────────────────────────

_compiled_workflow = None


def get_compiled_workflow():
    """Get or compile the workflow (cached)."""
    global _compiled_workflow
    if _compiled_workflow is None:
        workflow = build_credit_appraisal_workflow()
        _compiled_workflow = workflow.compile()
        logger.info("Workflow v2.0 compiled successfully")
    return _compiled_workflow


async def run_credit_appraisal(
    analysis_id: str,
    company_name: str,
    sector: str,
    document_paths: List[str],
    due_diligence_notes: str = "",
    loan_amount_requested: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Execute the full credit appraisal workflow v2.0.

    Args:
        analysis_id: Unique identifier for this analysis
        company_name: Name of the company
        sector: Industry sector
        document_paths: List of uploaded document file paths
        due_diligence_notes: Additional notes from the analyst
        loan_amount_requested: Requested loan amount in INR

    Returns:
        Final workflow state containing the CAM report
    """
    logger.info(
        f"Starting credit appraisal workflow v{WORKFLOW_VERSION} "
        f"for: {company_name} (ID: {analysis_id})"
    )

    initial_state = create_initial_state(
        analysis_id=analysis_id,
        company_name=company_name,
        sector=sector,
        document_paths=document_paths,
        due_diligence_notes=due_diligence_notes,
        loan_amount_requested=loan_amount_requested,
    )

    compiled = get_compiled_workflow()

    try:
        final_state = await compiled.ainvoke(initial_state)
        logger.info(
            f"Workflow completed for {company_name}. "
            f"Status: {final_state.get('status')}"
        )
        return final_state
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        # Persist failure status to Supabase
        await _persist_status(
            {"analysis_id": analysis_id},
            AnalysisStatus.FAILED.value,
        )
        return {
            **initial_state,
            "status": AnalysisStatus.FAILED.value,
            "errors": [f"Workflow execution failed: {str(e)}"],
        }
