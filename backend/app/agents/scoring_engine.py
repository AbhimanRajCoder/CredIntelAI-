"""
Deterministic Credit Scoring Engine for Intelli-Credit.
Computes credit score using a weighted formula — LLM only explains the result.
"""

import logging
from typing import Any, Dict, Optional

from app.agents.tools import (
    compute_debt_to_equity,
    compute_interest_coverage,
    compute_net_profit_margin,
    sector_risk_score as lookup_sector_score,
)
from app.models.state import CreditScore

logger = logging.getLogger(__name__)


# ─── Scoring Weights ──────────────────────────────────────────────────────────

WEIGHTS = {
    "financial": 0.50,
    "sector": 0.20,
    "promoter": 0.20,
    "news": 0.10,
}


# ─── Sub-Score Computations ───────────────────────────────────────────────────

def _compute_financial_score(metrics: Dict[str, Any]) -> float:
    """
    Compute financial sub-score (0-100) from extracted metrics.
    Higher = better financial health.
    """
    score = 50.0  # Base score

    # Debt-to-Equity ratio
    dte = metrics.get("debt_to_equity_ratio")
    if dte is not None:
        if dte < 0.5:
            score += 15
        elif dte < 1.0:
            score += 10
        elif dte < 1.5:
            score += 5
        elif dte < 2.0:
            score -= 5
        elif dte < 3.0:
            score -= 15
        else:
            score -= 25

    # Interest Coverage Ratio
    icr = metrics.get("interest_coverage_ratio")
    if icr is not None:
        if icr > 5:
            score += 15
        elif icr > 3:
            score += 10
        elif icr > 1.5:
            score += 0
        elif icr > 1:
            score -= 10
        else:
            score -= 20

    # Net Profit Margin
    npm = metrics.get("net_profit_margin")
    if npm is not None:
        if npm > 20:
            score += 10
        elif npm > 10:
            score += 5
        elif npm > 0:
            score += 0
        else:
            score -= 15

    # Current Ratio
    cr = metrics.get("current_ratio")
    if cr is not None:
        if cr > 2:
            score += 5
        elif cr > 1.5:
            score += 3
        elif cr > 1:
            score += 0
        else:
            score -= 10

    # Profitability
    profit = metrics.get("profit")
    if profit is not None and profit < 0:
        score -= 15

    # Revenue presence
    revenue = metrics.get("revenue")
    if revenue is not None and revenue > 0:
        score += 5

    return max(0, min(100, score))


def _compute_promoter_score(research_signals: Dict[str, Any]) -> float:
    """Compute promoter sub-score (0-100) from research signals."""
    score = 60.0  # Base

    risk = str(research_signals.get("promoter_risk", "unknown")).lower()
    if risk == "low":
        score += 25
    elif risk == "moderate":
        score += 5
    elif risk == "high":
        score -= 25

    # Check for specific risk signals
    promoter_profile = research_signals.get("promoter_profile", {})
    if isinstance(promoter_profile, dict):
        controversies = promoter_profile.get("controversies", [])
        if isinstance(controversies, list) and len(controversies) > 2:
            score -= 15

        rep_score = promoter_profile.get("promoter_reputation_score")
        if rep_score is not None:
            # Blend reputation into score
            score = score * 0.6 + float(rep_score) * 0.4

    return max(0, min(100, score))


def _compute_news_score(research_signals: Dict[str, Any]) -> float:
    """Compute news/sentiment sub-score (0-100). Higher = better (less negative news)."""
    score = 70.0  # Base

    negative_news = research_signals.get("negative_news", [])
    if isinstance(negative_news, list):
        neg_count = len(negative_news)
        if neg_count == 0:
            score += 15
        elif neg_count <= 2:
            score -= 5
        elif neg_count <= 5:
            score -= 20
        else:
            score -= 35

    return max(0, min(100, score))


def _score_to_grade(score: float) -> str:
    """Convert numeric score to credit grade."""
    if score >= 85:
        return "AAA"
    elif score >= 75:
        return "AA"
    elif score >= 65:
        return "A"
    elif score >= 55:
        return "BBB"
    elif score >= 45:
        return "BB"
    elif score >= 35:
        return "B"
    elif score >= 25:
        return "CCC"
    elif score >= 15:
        return "CC"
    elif score >= 10:
        return "C"
    else:
        return "D"


def _score_to_risk_level(score: float) -> str:
    """Convert score to risk level."""
    if score >= 70:
        return "low"
    elif score >= 50:
        return "moderate"
    elif score >= 30:
        return "high"
    else:
        return "very_high"


# ─── Main Scoring Function ───────────────────────────────────────────────────

def compute_credit_score(
    financial_metrics: Dict[str, Any],
    research_signals: Dict[str, Any],
    sector: str,
    trend_analysis: Optional[Dict[str, Any]] = None,
    fraud_signals: Optional[Dict[str, Any]] = None,
) -> CreditScore:
    """
    Compute deterministic credit score using the weighted formula:

        credit_score = financial × 0.50 + sector × 0.20
                     + promoter × 0.20 + news × 0.10

    Additional adjustments for trend analysis and fraud signals.

    Args:
        financial_metrics: Extracted financial metrics dict
        research_signals: Research agent output dict
        sector: Company sector string
        trend_analysis: Optional trend analysis dict
        fraud_signals: Optional fraud detection dict

    Returns:
        CreditScore Pydantic model with deterministic score
    """
    # Compute sub-scores
    financial_score = _compute_financial_score(financial_metrics)
    sector_score_val = lookup_sector_score(sector)
    promoter_score = _compute_promoter_score(research_signals)
    news_score = _compute_news_score(research_signals)

    # Weighted total
    total = (
        financial_score * WEIGHTS["financial"]
        + sector_score_val * WEIGHTS["sector"]
        + promoter_score * WEIGHTS["promoter"]
        + news_score * WEIGHTS["news"]
    )

    # Trend adjustments (+/- up to 5 points)
    if trend_analysis:
        cagr = trend_analysis.get("revenue_cagr")
        if cagr is not None:
            if cagr > 15:
                total += 5
            elif cagr > 5:
                total += 2
            elif cagr < -5:
                total -= 5

        debt_traj = trend_analysis.get("debt_trajectory", "")
        if debt_traj == "accelerating":
            total -= 3
        elif debt_traj == "decreasing":
            total += 3

    # Fraud penalty (0 to -15 points)
    if fraud_signals:
        fraud_score_val = fraud_signals.get("fraud_score", 0)
        if fraud_score_val > 50:
            total -= 15
        elif fraud_score_val > 30:
            total -= 8
        elif fraud_score_val > 10:
            total -= 3

    total = max(0, min(100, round(total, 1)))
    grade = _score_to_grade(total)
    risk_level = _score_to_risk_level(total)

    logger.info(
        f"Credit score computed: total={total}, grade={grade}, risk={risk_level} "
        f"(fin={financial_score:.0f}, sec={sector_score_val:.0f}, "
        f"promo={promoter_score:.0f}, news={news_score:.0f})"
    )

    return CreditScore(
        total_score=total,
        financial_score=round(financial_score, 1),
        sector_score=round(sector_score_val, 1),
        promoter_score=round(promoter_score, 1),
        news_score=round(news_score, 1),
        risk_level=risk_level,
        grade=grade,
        explanation="",  # To be filled by LLM in risk agent
    )
