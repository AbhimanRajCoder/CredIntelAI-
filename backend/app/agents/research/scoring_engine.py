"""
Research Scoring Engine for corporate intelligence.
Converts structured risk signals into a numerical research score (0-100).
"""

import logging
from typing import List

from app.models.schemas import RiskSignal

logger = logging.getLogger(__name__)

# Signal weights: negative values reduce the score, positive values increase it
SIGNAL_WEIGHTS = {
    "fraud": -45,
    "litigation": -15,
    "regulatory_penalty": -20,
    "debt_restructuring": -25,
    "promoter_controversy": -20,
    "insolvency_filing": -40,
    "sector_slowdown": -12,
    "industry_expansion": +8,
    "government_support": +4,
}

# Severity multipliers
SEVERITY_MULTIPLIERS = {
    "low": 0.4,
    "medium": 0.8,
    "high": 1.4,
}

BASELINE_SCORE = 80.0


def compute_research_score(
    signals: List[RiskSignal],
    promoter_score: float = 60.0,
    sector_outlook: str = "unknown",
) -> float:
    """
    Compute a composite research score from risk signals and intelligence data.

    Refined logic:
    - Score starts at BASELINE_SCORE (80)
    - Significant damping for many low-severity signals to prevent score collapse.
    - Promoter and Sector influence.
    """
    score = BASELINE_SCORE
    
    # Track signal impact to prevent runaway negative score from minor items
    negative_adjustments = []
    positive_adjustments = []

    for signal in signals:
        weight = SIGNAL_WEIGHTS.get(signal.type, 0)
        multiplier = SEVERITY_MULTIPLIERS.get(signal.severity, 1.0)
        adj = weight * multiplier
        
        if adj < 0:
            negative_adjustments.append(adj)
        else:
            positive_adjustments.append(adj)

    # Apply damping to negative adjustments if there are many
    # Formula: top 3 count fully, others damped by 70%
    negative_adjustments.sort() # Most negative first
    total_neg = 0
    for i, adj in enumerate(negative_adjustments):
        if i < 3:
            total_neg += adj
        else:
            total_neg += (adj * 0.3)
            
    score += total_neg
    score += sum(positive_adjustments)

    # Promoter reputation influence (±15 points)
    # Scale: 0-100. Let's map it to an adjustment.
    # If 80+, +5. If <40, -15. If 40-60, -5.
    if promoter_score < 40:
        score -= 15
    elif promoter_score < 60:
        score -= 5
    elif promoter_score >= 85:
        score += 5

    # Sector outlook influence
    sector_adj = {
        "positive": +5,
        "moderate": 0,
        "negative": -12,
        "unknown": 0,
    }
    score += sector_adj.get(sector_outlook, 0)

    # Clamp to [0, 100]
    final_score = max(0.0, min(100.0, score))

    logger.info(
        f"Research score refinement: baseline={BASELINE_SCORE}, "
        f"neg_adj={total_neg:.1f}, pos_adj={sum(positive_adjustments):.1f}, "
        f"promoter_score={promoter_score}, final={final_score:.1f}"
    )

    return round(final_score, 1)
