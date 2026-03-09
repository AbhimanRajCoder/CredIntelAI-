"""
Intelli-Credit: Production Workflow State Models.
Pydantic-based typed state for the LangGraph credit appraisal pipeline.
All agents interact with validated structured state objects.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


# ─── Workflow Version ─────────────────────────────────────────────────────────

WORKFLOW_VERSION = "2.0.0"


# ─── Reasoning & Explainability ───────────────────────────────────────────────

class ReasoningStep(BaseModel):
    """A single reasoning step in the explainability trace."""
    agent: str = Field(..., description="Agent that produced this reasoning")
    decision: str = Field(..., description="What was decided")
    evidence: str = Field("", description="Evidence or data supporting the decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Agent Observability ──────────────────────────────────────────────────────

class AgentMetrics(BaseModel):
    """Performance metrics for a single agent execution."""
    agent_name: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str = "pending"  # pending | running | success | failed | timeout
    error: Optional[str] = None
    retries: int = 0


# ─── Fraud Detection ─────────────────────────────────────────────────────────

class FraudFlag(BaseModel):
    """A single fraud/anomaly signal."""
    signal: str = Field(..., description="Description of the fraud signal")
    severity: str = Field("medium", description="low | medium | high")
    evidence: str = Field("", description="Supporting data or observation")
    weight: float = Field(1.0, ge=0, le=10, description="Weight in fraud score")


class FraudSignals(BaseModel):
    """Output from the Fraud Detection Agent."""
    flags: List[FraudFlag] = Field(default_factory=list)
    fraud_score: float = Field(0.0, ge=0, le=100, description="Composite fraud score")
    summary: str = Field("", description="Brief narrative summary")


# ─── Trend Analysis ──────────────────────────────────────────────────────────

class TrendAnalysis(BaseModel):
    """Output from the Multi-Year Trend Agent."""
    revenue_cagr: Optional[float] = Field(None, description="Revenue CAGR %")
    ebitda_trend: str = Field("unknown", description="growing | stable | declining | unknown")
    debt_trajectory: str = Field("unknown", description="accelerating | stable | decreasing | unknown")
    cash_flow_stability: Optional[float] = Field(None, description="Coefficient of variation")
    profit_volatility: Optional[float] = Field(None, description="Std dev of profit margins")
    debt_growth_rate: Optional[float] = Field(None, description="Annual debt growth %")
    years_analyzed: int = Field(0, description="Number of fiscal years available")
    summary: str = Field("", description="Brief narrative summary")


# ─── Validation / Quality Gate ────────────────────────────────────────────────

class QualityCheck(BaseModel):
    """A single quality check result."""
    check_name: str
    passed: bool
    details: str = ""


class ValidationResult(BaseModel):
    """Output from the Validation Agent (quality gate)."""
    quality_score: float = Field(0.0, ge=0, le=100, description="Overall quality score")
    confidence_score: float = Field(0.0, ge=0, le=1.0, description="Composite confidence 0-1")
    ocr_quality: float = Field(0.0, ge=0, le=1.0)
    data_completeness: float = Field(0.0, ge=0, le=1.0)
    source_reliability: float = Field(0.0, ge=0, le=1.0)
    checks: List[QualityCheck] = Field(default_factory=list)
    is_acceptable: bool = Field(True, description="Whether quality meets threshold")
    summary: str = Field("")


# ─── Credit Scoring ──────────────────────────────────────────────────────────

class CreditScore(BaseModel):
    """Output from the Deterministic Credit Scoring Engine."""
    total_score: float = Field(0.0, ge=0, le=100)
    financial_score: float = Field(0.0, ge=0, le=100)
    sector_score: float = Field(0.0, ge=0, le=100)
    promoter_score: float = Field(0.0, ge=0, le=100)
    news_score: float = Field(0.0, ge=0, le=100)
    risk_level: str = Field("moderate", description="low | moderate | high | very_high")
    grade: str = Field("BBB", description="AAA through D")
    explanation: str = Field("", description="LLM-generated explanation of the score")


# ─── Structured Risk Factors ─────────────────────────────────────────────────

class RiskFactor(BaseModel):
    """A typed risk factor for CAM reporting."""
    factor: str = Field(..., description="Risk factor description")
    severity: str = Field("medium", description="low | medium | high")
    category: str = Field("general", description="financial | operational | market | regulatory | promoter")


class StrengthFactor(BaseModel):
    """A typed strength factor for CAM reporting."""
    factor: str = Field(..., description="Strength description")
    category: str = Field("general", description="financial | operational | market | regulatory | promoter")


class StructuredRiskFactors(BaseModel):
    """Combined risk and strength factors from guardrailed Risk Agent."""
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    strength_factors: List[StrengthFactor] = Field(default_factory=list)


# ─── Financial Extraction ────────────────────────────────────────────────────

class ExtractedFinancials(BaseModel):
    """Output from the Financial Extraction Agent — multi-year data."""
    metrics_by_year: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Fiscal year → FinancialMetrics dict, e.g. {'FY2024': {...}, 'FY2023': {...}}"
    )
    latest_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Most recent year's metrics (convenience)"
    )
    detected_sections: List[str] = Field(
        default_factory=list,
        description="Document sections found: balance_sheet, pnl, cash_flow, etc."
    )
    extraction_method: str = Field(
        "unknown",
        description="table_parser | llm_fallback | hybrid"
    )
    fiscal_years_found: List[str] = Field(default_factory=list)


# ─── LangGraph TypedDict State ───────────────────────────────────────────────
# LangGraph requires TypedDict. We keep both: TypedDict for the graph,
# and Pydantic models for sub-structures (serialized as dicts in state).

class CreditAppraisalState(TypedDict, total=False):
    """Typed state for the LangGraph credit appraisal workflow."""

    # ── Workflow metadata ────────────────────────────────────────────────────
    workflow_version: str
    created_at: str          # ISO datetime string
    updated_at: str          # ISO datetime string

    # ── Inputs ───────────────────────────────────────────────────────────────
    analysis_id: str
    company_name: str
    sector: str
    due_diligence_notes: str
    loan_amount_requested: Optional[float]
    document_paths: List[str]

    # ── Data Ingestor outputs ────────────────────────────────────────────────
    has_documents: bool
    extracted_text: str
    reconstructed_tables: List[Dict[str, Any]]     # from document parser
    detected_sections: List[str]                    # from section detector

    # ── Financial Extraction outputs ─────────────────────────────────────────
    financial_metrics: Dict[str, Any]               # latest year (backwards compat)
    extracted_financials: Dict[str, Any]             # ExtractedFinancials.model_dump()

    # ── Validation gate ──────────────────────────────────────────────────────
    validation_result: Dict[str, Any]               # ValidationResult.model_dump()

    # ── Parallel agents outputs ──────────────────────────────────────────────
    research_signals: Dict[str, Any]
    trend_analysis: Dict[str, Any]                  # TrendAnalysis.model_dump()
    fraud_signals: Dict[str, Any]                   # FraudSignals.model_dump()

    # ── Scoring & Risk ───────────────────────────────────────────────────────
    credit_score: Dict[str, Any]                    # CreditScore.model_dump()
    risk_analysis: Dict[str, Any]
    structured_risk_factors: Dict[str, Any]         # StructuredRiskFactors.model_dump()

    # ── CAM Output ───────────────────────────────────────────────────────────
    cam_report: Dict[str, Any]

    # ── Workflow control ─────────────────────────────────────────────────────
    status: str
    errors: List[str]
    current_agent: str

    # ── Observability ────────────────────────────────────────────────────────
    reasoning_trace: List[Dict[str, Any]]           # List[ReasoningStep.model_dump()]
    agent_metrics: Dict[str, Dict[str, Any]]        # agent_name → AgentMetrics.model_dump()


# ─── State Helpers ────────────────────────────────────────────────────────────

def create_initial_state(
    analysis_id: str,
    company_name: str,
    sector: str,
    document_paths: List[str],
    due_diligence_notes: str = "",
    loan_amount_requested: Optional[float] = None,
) -> CreditAppraisalState:
    """Create a fully initialized workflow state."""
    now = datetime.utcnow().isoformat()
    return CreditAppraisalState(
        workflow_version=WORKFLOW_VERSION,
        created_at=now,
        updated_at=now,
        analysis_id=analysis_id,
        company_name=company_name,
        sector=sector,
        due_diligence_notes=due_diligence_notes,
        loan_amount_requested=loan_amount_requested,
        document_paths=document_paths,
        has_documents=len(document_paths) > 0,
        extracted_text="",
        reconstructed_tables=[],
        detected_sections=[],
        financial_metrics={},
        extracted_financials={},
        validation_result={},
        research_signals={},
        trend_analysis={},
        fraud_signals={},
        credit_score={},
        risk_analysis={},
        structured_risk_factors={},
        cam_report={},
        status="pending",
        errors=[],
        current_agent="",
        reasoning_trace=[],
        agent_metrics={},
    )


def add_reasoning_step(
    state: Dict[str, Any],
    agent: str,
    decision: str,
    evidence: str = "",
) -> List[Dict[str, Any]]:
    """Append a reasoning step to the trace. Returns updated trace list."""
    trace = list(state.get("reasoning_trace", []))
    step = ReasoningStep(agent=agent, decision=decision, evidence=evidence)
    trace.append(step.model_dump(mode="json"))
    return trace


def add_agent_metrics(
    state: Dict[str, Any],
    metrics: AgentMetrics,
) -> Dict[str, Dict[str, Any]]:
    """Add agent metrics to state. Returns updated metrics dict."""
    all_metrics = dict(state.get("agent_metrics", {}))
    all_metrics[metrics.agent_name] = metrics.model_dump(mode="json")
    return all_metrics
