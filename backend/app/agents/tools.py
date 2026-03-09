"""
Deterministic Financial Tools for Intelli-Credit.
Pure functions for computing financial ratios and sector scores.
These replace LLM-based computations to eliminate hallucination risk.
"""

import logging
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Ratio Computations ──────────────────────────────────────────────────────

def compute_debt_to_equity(total_debt: float, total_equity: float) -> Optional[float]:
    """Debt-to-Equity ratio. Lower is better (< 1 ideal, > 2 high risk)."""
    if total_equity == 0:
        return None
    return round(total_debt / total_equity, 2)


def compute_interest_coverage(ebit: float, interest_expense: float) -> Optional[float]:
    """Interest Coverage Ratio. Higher is better (> 3 comfortable, < 1.5 risky)."""
    if interest_expense == 0:
        return None
    return round(ebit / interest_expense, 2)


def compute_current_ratio(current_assets: float, current_liabilities: float) -> Optional[float]:
    """Current Ratio. Measures short-term liquidity. Ideal: 1.5-3.0."""
    if current_liabilities == 0:
        return None
    return round(current_assets / current_liabilities, 2)


def compute_net_profit_margin(net_profit: float, revenue: float) -> Optional[float]:
    """Net Profit Margin %. Higher is better."""
    if revenue == 0:
        return None
    return round((net_profit / revenue) * 100, 2)


def compute_return_on_equity(net_profit: float, shareholder_equity: float) -> Optional[float]:
    """Return on Equity %. Higher is better (> 15% excellent)."""
    if shareholder_equity == 0:
        return None
    return round((net_profit / shareholder_equity) * 100, 2)


def compute_revenue_cagr(revenues: List[float], years: int) -> Optional[float]:
    """
    Compound Annual Growth Rate for revenue (or any series).

    Args:
        revenues: List of values [oldest, ..., newest]
        years: Number of years between first and last value

    Returns:
        CAGR as percentage (e.g., 10.0 for 10%)
    """
    if not revenues or len(revenues) < 2 or years <= 0:
        return None
    if revenues[0] <= 0:
        return None
    ratio = revenues[-1] / revenues[0]
    if ratio <= 0:
        return None
    cagr = (ratio ** (1 / years) - 1) * 100
    return round(cagr, 2)


def compute_debt_growth_rate(debts: List[float]) -> Optional[float]:
    """
    Annual debt growth rate (using latest two values).

    Returns:
        Growth rate as percentage
    """
    if not debts or len(debts) < 2:
        return None
    if debts[-2] == 0:
        return None
    rate = ((debts[-1] - debts[-2]) / abs(debts[-2])) * 100
    return round(rate, 2)


def compute_profit_volatility(profits: List[float]) -> Optional[float]:
    """
    Standard deviation of profit values as a measure of volatility.

    Returns:
        Coefficient of variation (std_dev / mean) as percentage
    """
    if not profits or len(profits) < 2:
        return None
    mean = sum(profits) / len(profits)
    if mean == 0:
        return None
    variance = sum((p - mean) ** 2 for p in profits) / len(profits)
    std_dev = math.sqrt(variance)
    return round((std_dev / abs(mean)) * 100, 2)


def compute_cash_flow_stability(cash_flows: List[float]) -> Optional[float]:
    """
    Coefficient of variation for cash flows (lower = more stable).

    Returns:
        CV as decimal (0-1 range typical for stable companies)
    """
    if not cash_flows or len(cash_flows) < 2:
        return None
    mean = sum(cash_flows) / len(cash_flows)
    if mean == 0:
        return None
    variance = sum((cf - mean) ** 2 for cf in cash_flows) / len(cash_flows)
    std_dev = math.sqrt(variance)
    return round(std_dev / abs(mean), 3)


# ─── Sector Risk Scoring ─────────────────────────────────────────────────────

SECTOR_RISK_SCORES: Dict[str, float] = {
    # Low risk sectors (score 70-90 = good)
    "fmcg": 82,
    "consumer goods": 82,
    "pharmaceuticals": 78,
    "pharma": 78,
    "healthcare": 78,
    "it": 80,
    "technology": 80,
    "information technology": 80,
    "software": 80,

    # Moderate risk (50-70)
    "manufacturing": 65,
    "auto": 62,
    "automobile": 62,
    "automotive": 62,
    "chemicals": 60,
    "cement": 58,
    "textiles": 55,
    "telecom": 60,
    "telecommunications": 60,
    "power": 55,
    "energy": 55,
    "utilities": 60,
    "banking": 65,
    "financial services": 65,
    "nbfc": 55,

    # High risk (30-50)
    "real estate": 42,
    "construction": 45,
    "infrastructure": 48,
    "steel": 45,
    "metals": 45,
    "mining": 42,
    "aviation": 38,
    "airlines": 38,
    "shipping": 40,
    "logistics": 50,

    # Very high risk (< 30)
    "crypto": 15,
    "cryptocurrency": 15,
    "gems and jewellery": 35,
}


def sector_risk_score(sector: str) -> float:
    """
    Look up sector risk score. Higher = lower risk (better for creditworthiness).

    Returns: Score 0-100 (default 50 for unknown sectors)
    """
    if not sector:
        return 50.0

    sector_lower = sector.lower().strip()

    # Try exact match
    if sector_lower in SECTOR_RISK_SCORES:
        return SECTOR_RISK_SCORES[sector_lower]

    # Try partial match
    for key, score in SECTOR_RISK_SCORES.items():
        if key in sector_lower or sector_lower in key:
            return score

    logger.debug(f"Unknown sector '{sector}', using default score 50")
    return 50.0
