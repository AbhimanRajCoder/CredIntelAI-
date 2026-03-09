"""
Risk Analysis Agent for Intelli-Credit.
Uses deterministic credit scoring + guardrailed LLM for explanation only.
"""

import json
import logging
from typing import Any, Dict

from app.models.schemas import RiskAnalysis, RiskGrade, AnalysisStatus
from app.models.state import (
    RiskFactor, StrengthFactor, StructuredRiskFactors,
    add_reasoning_step,
)
from app.agents.scoring_engine import compute_credit_score
from app.services.groq_client import get_groq_client
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)

# Valid risk grades
VALID_GRADES = {g.value for g in RiskGrade}


def _normalize_grade(grade_str: str) -> str:
    """Normalize risk grade string to valid enum value."""
    grade_upper = grade_str.upper().strip()
    if grade_upper in VALID_GRADES:
        return grade_upper
    grade_map = {
        "A+": "AA", "A-": "A", "B+": "BB", "B-": "B",
        "BBB+": "BBB", "BBB-": "BBB", "BB+": "BB", "BB-": "BB",
        "CCC+": "CCC", "CCC-": "CCC",
    }
    return grade_map.get(grade_upper, "BBB")


# ─── Guardrailed Risk Prompt ─────────────────────────────────────────────────
# LLM only receives structured data — no raw text
GUARDRAILED_RISK_PROMPT = """You are a senior credit risk analyst at a major Indian bank.

You are given STRUCTURED DATA from our automated analysis pipeline. Based ONLY on this data, provide:
1. An explanation of the overall credit risk (200-300 words)
2. Top 5 risk factors with severity and category
3. Top 5 strength factors with category

**Company:** {company_name}
**Sector:** {sector}

**Credit Score (Deterministic):**
- Total Score: {total_score}/100
- Financial Score: {financial_score}/100
- Sector Score: {sector_score}/100
- Promoter Score: {promoter_score}/100
- News Score: {news_score}/100
- Risk Level: {risk_level}
- Grade: {grade}

**Financial Metrics:**
{financial_metrics}

**Trend Analysis:**
{trend_analysis}

**Fraud Signals:**
{fraud_signals}

**Research Signals:**
{research_signals}

**Due Diligence Notes:**
{due_diligence_notes}

IMPORTANT: Base your analysis ONLY on the structured data above. Do not invent numbers or facts.

Respond ONLY in valid JSON:
{{
    "explanation": "<200-300 word analysis>",
    "risk_factors": [
        {{"factor": "<description>", "severity": "low|medium|high", "category": "financial|operational|market|regulatory|promoter"}}
    ],
    "strength_factors": [
        {{"factor": "<description>", "category": "financial|operational|market|regulatory|promoter"}}
    ]
}}
"""


@track_agent(timeout=45)
async def risk_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Risk Analysis Agent: Deterministic scoring + guardrailed LLM explanation.

    Pipeline:
        1. Compute deterministic credit score (scoring_engine)
        2. Send ONLY structured data to LLM for explanation
        3. Parse structured risk/strength factors
        4. Build RiskAnalysis and StructuredRiskFactors
    """
    logger.info("RISK ANALYSIS AGENT: Starting credit risk assessment")

    company_name = state.get("company_name", "")
    sector = state.get("sector", "")
    financial_metrics = state.get("financial_metrics", {})
    research_signals = state.get("research_signals", {})
    trend_analysis = state.get("trend_analysis", {})
    fraud_signals = state.get("fraud_signals", {})
    due_diligence_notes = state.get("due_diligence_notes", "")
    errors = list(state.get("errors", []))

    # ── Step 1: Deterministic credit scoring ──────────────────────────────
    credit_score = compute_credit_score(
        financial_metrics=financial_metrics,
        research_signals=research_signals,
        sector=sector,
        trend_analysis=trend_analysis,
        fraud_signals=fraud_signals,
    )

    # ── Step 2: LLM explanation (guardrailed) ─────────────────────────────
    risk_factors = []
    strength_factors = []
    explanation = ""

    try:
        groq = get_groq_client()

        prompt = GUARDRAILED_RISK_PROMPT.format(
            company_name=company_name,
            sector=sector,
            total_score=credit_score.total_score,
            financial_score=credit_score.financial_score,
            sector_score=credit_score.sector_score,
            promoter_score=credit_score.promoter_score,
            news_score=credit_score.news_score,
            risk_level=credit_score.risk_level,
            grade=credit_score.grade,
            financial_metrics=json.dumps(financial_metrics, indent=2, default=str),
            trend_analysis=json.dumps(trend_analysis, indent=2, default=str),
            fraud_signals=json.dumps(fraud_signals, indent=2, default=str),
            research_signals=json.dumps(research_signals, indent=2, default=str),
            due_diligence_notes=due_diligence_notes or "None provided.",
        )

        result = await groq.generate_json(
            prompt=prompt,
            system_message=(
                "You are a senior credit risk analyst. Provide rigorous, data-driven "
                "analysis based ONLY on the structured data given. Never invent facts."
            ),
        )

        explanation = result.get("explanation", "Risk analysis completed.")

        # Parse risk factors
        raw_risks = result.get("risk_factors", [])
        for rf in raw_risks[:7]:
            if isinstance(rf, dict):
                risk_factors.append(RiskFactor(
                    factor=rf.get("factor", ""),
                    severity=rf.get("severity", "medium"),
                    category=rf.get("category", "general"),
                ))

        # Parse strength factors
        raw_strengths = result.get("strength_factors", [])
        for sf in raw_strengths[:7]:
            if isinstance(sf, dict):
                strength_factors.append(StrengthFactor(
                    factor=sf.get("factor", ""),
                    category=sf.get("category", "general"),
                ))

    except Exception as e:
        error_msg = f"LLM risk explanation failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        explanation = "Risk analysis explanation could not be generated. Manual review recommended."

    # ── Step 3: Build outputs ─────────────────────────────────────────────
    credit_score.explanation = explanation

    risk_grade_str = _normalize_grade(credit_score.grade)

    risk_analysis = RiskAnalysis(
        risk_score=credit_score.total_score,
        risk_grade=RiskGrade(risk_grade_str),
        key_risks=[rf.factor for rf in risk_factors[:5]],
        strengths=[sf.factor for sf in strength_factors[:5]],
        explanation=explanation,
    )

    structured_risk = StructuredRiskFactors(
        risk_factors=risk_factors,
        strength_factors=strength_factors,
    )

    reasoning_trace = add_reasoning_step(
        state,
        agent="risk_agent",
        decision=(
            f"Credit score: {credit_score.total_score}/100, "
            f"Grade: {credit_score.grade}, Risk: {credit_score.risk_level}"
        ),
        evidence=(
            f"Financial={credit_score.financial_score}, "
            f"Sector={credit_score.sector_score}, "
            f"Promoter={credit_score.promoter_score}, "
            f"News={credit_score.news_score}"
        ),
    )

    logger.info(
        f"RISK ANALYSIS AGENT: Complete — score={credit_score.total_score}, "
        f"grade={credit_score.grade}, risk={credit_score.risk_level}"
    )

    return {
        **state,
        "credit_score": credit_score.model_dump(),
        "risk_analysis": risk_analysis.model_dump() if risk_analysis else {},
        "structured_risk_factors": structured_risk.model_dump(),
        "status": AnalysisStatus.ANALYZING_RISK.value,
        "current_agent": "risk_agent",
        "errors": errors,
        "reasoning_trace": reasoning_trace,
    }
