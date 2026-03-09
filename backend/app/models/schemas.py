from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
import re


# ─── Enums ────────────────────────────────────────────────────────────────────

class RiskGrade(str, Enum):
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"


class LoanDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CONDITIONAL_APPROVE = "CONDITIONAL_APPROVE"


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    PENDING = "pending"
    PROCESSING = "processing"
    PARSING_DOCUMENTS = "parsing_documents"
    EXTRACTING_FINANCIALS = "extracting_financials"
    INGESTING = "ingesting"
    RESEARCHING = "researching"
    RESEARCHING_COMPANY = "researching_company"
    PERFORMING_RISK_ANALYSIS = "performing_risk_analysis"
    ANALYZING_RISK = "analyzing_risk"
    GENERATING_CAM = "generating_cam"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


# ─── Request Models ──────────────────────────────────────────────────────────

class AnalyzeCompanyRequest(BaseModel):
    """Request model for company analysis."""
    company_name: str = Field(..., description="Name of the company to analyze")
    sector: str = Field(..., description="Industry sector of the company")
    due_diligence_notes: Optional[str] = Field(
        None, description="Additional due diligence notes from the analyst"
    )
    loan_amount_requested: Optional[float] = Field(
        None, description="Loan amount requested in INR"
    )


# ─── Financial Data Models ───────────────────────────────────────────────────

class FinancialMetrics(BaseModel):
    """Extracted financial metrics from documents."""
    revenue: Optional[float] = Field(None, description="Annual revenue in INR")
    profit: Optional[float] = Field(None, description="Net profit in INR")
    debt: Optional[float] = Field(None, description="Total debt in INR")
    cashflow: Optional[float] = Field(None, description="Operating cashflow in INR")
    bank_loans: Optional[float] = Field(None, description="Total bank loans in INR")
    litigation_mentions: int = Field(0, description="Number of litigation mentions found")
    promoter_names: List[str] = Field(default_factory=list, description="Names of key promoters/directors identified from documents")
    debt_to_equity_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage_ratio: Optional[float] = None
    net_profit_margin: Optional[float] = None
    return_on_equity: Optional[float] = None
    raw_extracted_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Raw extracted data from documents"
    )


# ─── Research Data Models ────────────────────────────────────────────────────

class ResearchSignals(BaseModel):
    """External research signals from web search."""
    promoter_risk: str = Field("unknown", description="Promoter reputation risk level")
    sector_risk: str = Field("unknown", description="Sector/industry risk level")
    litigation_count: int = Field(0, description="Number of litigation cases found")
    negative_news: List[str] = Field(
        default_factory=list, description="List of negative news items"
    )
    positive_news: List[str] = Field(
        default_factory=list, description="List of positive news items"
    )
    promoter_background: Optional[str] = Field(
        None, description="Summary of promoter background"
    )
    industry_outlook: Optional[str] = Field(
        None, description="Industry outlook summary"
    )
    regulatory_changes: Optional[str] = Field(
        None, description="Relevant regulatory changes"
    )
    sources: List[str] = Field(
        default_factory=list, description="URLs of sources used"
    )
    research_score: float = Field(50.0, ge=0, le=100, description="Composite research intelligence score")
    articles_analyzed: int = Field(0, description="Number of articles analyzed")
    sources_used: int = Field(0, description="Number of unique sources used")


# ─── Research Intelligence Models ────────────────────────────────────────────

class RiskSignal(BaseModel):
    """A single structured risk signal extracted from research articles."""
    type: str = Field(..., description="Signal type: fraud, litigation, regulatory_penalty, debt_restructuring, promoter_controversy, insolvency_filing, sector_slowdown, industry_expansion, government_support")
    severity: str = Field("medium", description="low, medium, or high")
    description: str = Field(..., description="Human-readable description of the signal")
    source: Optional[str] = Field(None, description="Source URL or publication name")
    date: Optional[str] = Field(None, description="Publication or event date")


class PromoterProfile(BaseModel):
    """Structured promoter background intelligence."""
    promoter_reputation_score: float = Field(50.0, ge=0, le=100)
    controversies: List[str] = Field(default_factory=list)
    previous_companies: List[str] = Field(default_factory=list)
    risk_level: str = Field("unknown", description="low, moderate, or high")
    summary: str = Field("", description="Narrative summary of promoter background")


class SectorIntelligence(BaseModel):
    """Structured sector and regulatory intelligence."""
    sector_outlook: str = Field("unknown", description="positive, moderate, or negative")
    regulatory_risk: str = Field("unknown", description="low, medium, or high")
    industry_headwinds: List[str] = Field(default_factory=list)
    industry_tailwinds: List[str] = Field(default_factory=list)
    summary: str = Field("", description="Narrative summary of sector outlook")


class ResearchReport(BaseModel):
    """Full structured output of the upgraded Research Agent."""
    promoter_profile: Optional[PromoterProfile] = None
    sector_intelligence: Optional[SectorIntelligence] = None
    risk_signals: List[RiskSignal] = Field(default_factory=list)
    positive_signals: List[str] = Field(default_factory=list)
    negative_signals: List[str] = Field(default_factory=list)
    research_score: float = Field(50.0, ge=0, le=100)
    sources: List[str] = Field(default_factory=list)
    articles_analyzed: int = Field(0, description="Total articles analyzed across all queries")
    sources_used: int = Field(0, description="Total unique domains/sources identified")


# ─── Risk Analysis Models ────────────────────────────────────────────────────

class RiskAnalysis(BaseModel):
    """Credit risk analysis results."""
    risk_score: float = Field(..., ge=0, le=100, description="Risk score out of 100")
    risk_grade: RiskGrade = Field(..., description="Credit risk grade")
    key_risks: List[str] = Field(
        default_factory=list, description="List of key risk factors"
    )
    strengths: List[str] = Field(
        default_factory=list, description="List of key strengths"
    )
    explanation: Optional[str] = Field(
        None, description="Detailed explanation of risk assessment"
    )


# ─── CAM Report Models ───────────────────────────────────────────────────────

class LendingRecommendation(BaseModel):
    """Final lending recommendation."""
    decision: LoanDecision = Field(..., description="Loan decision")
    suggested_loan_limit: Optional[float] = Field(
        None, description="Suggested loan limit in INR"
    )
    suggested_interest_rate: Optional[float] = Field(
        None, description="Suggested interest rate percentage"
    )
    explanation: str = Field(..., description="Explanation of the decision")
    conditions: List[str] = Field(
        default_factory=list, description="Conditions for approval"
    )

    @field_validator("suggested_loan_limit", "suggested_interest_rate", mode="before")
    @classmethod
    def clean_numeric_fields(cls, v):
        if isinstance(v, str):
            # Remove %, ₹, commas, and spaces
            cleaned = re.sub(r"[^\d.-]", "", v)
            try:
                return float(cleaned)
            except ValueError:
                return None
        return v


class CAMReport(BaseModel):
    """Complete Credit Appraisal Memo."""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    sector: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Core Sections
    executive_summary: str = ""
    company_overview: str = ""
    promoter_background: str = ""
    financial_analysis: str = ""
    industry_outlook: str = ""
    risk_assessment: str = ""
    lending_recommendation_text: str = ""

    # New Sections (v2.0)
    trend_analysis_section: str = ""
    fraud_signals_section: str = ""
    reasoning_trace_section: str = ""
    data_quality_section: str = ""

    # Structured Data
    financial_metrics: Optional[FinancialMetrics] = None
    research_signals: Optional[ResearchSignals] = None
    risk_analysis: Optional[RiskAnalysis] = None
    recommendation: Optional[LendingRecommendation] = None

    # v2.0 Structured Data
    credit_score: Optional[Dict[str, Any]] = None
    trend_analysis_data: Optional[Dict[str, Any]] = None
    fraud_signals_data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    reasoning_trace: Optional[List[Dict[str, Any]]] = None

    # File paths
    docx_path: Optional[str] = None
    pdf_path: Optional[str] = None
    json_path: Optional[str] = None

# NOTE: WorkflowState has been moved to app.models.state (CreditAppraisalState)
# Kept as a comment for reference during migration.



# ─── Response Models ─────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response for document upload."""
    message: str
    analysis_id: str
    uploaded_files: List[str]
    file_count: int


class AnalysisResponse(BaseModel):
    """Response for analysis trigger."""
    message: str
    analysis_id: str
    status: AnalysisStatus
    created_at: Optional[datetime] = None


class ReportResponse(BaseModel):
    """Response for report retrieval."""
    analysis_id: str
    status: AnalysisStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    report: Optional[CAMReport] = None
    docx_download_url: Optional[str] = None
    pdf_download_url: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
