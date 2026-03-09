"""
Multi-Year Trend Analysis Agent for Intelli-Credit.
Evaluates revenue growth, EBITDA trend, debt trajectory, and cash flow stability.
"""

import logging
from typing import Any, Dict, List

from app.agents.tools import (
    compute_revenue_cagr,
    compute_debt_growth_rate,
    compute_profit_volatility,
    compute_cash_flow_stability,
)
from app.models.state import TrendAnalysis, add_reasoning_step
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)


@track_agent(timeout=30)
async def trend_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trend Analysis Agent: Evaluate multi-year financial trends.

    Input: extracted_financials.metrics_by_year
    Output: TrendAnalysis stored in state
    """
    logger.info("TREND AGENT: Analyzing multi-year financial trends")

    extracted_financials = state.get("extracted_financials", {})
    metrics_by_year = extracted_financials.get("metrics_by_year", {})
    errors = list(state.get("errors", []))

    trend = TrendAnalysis(years_analyzed=len(metrics_by_year))

    if len(metrics_by_year) < 2:
        trend.summary = "Insufficient multi-year data for trend analysis (need ≥ 2 years)."
        logger.info("TREND AGENT: Insufficient data for trend analysis")

        reasoning_trace = add_reasoning_step(
            state,
            agent="trend_agent",
            decision="Skipped — insufficient multi-year data",
            evidence=f"Only {len(metrics_by_year)} year(s) available",
        )

        return {
            **state,
            "trend_analysis": trend.model_dump(),
            "current_agent": "trend_agent",
            "reasoning_trace": reasoning_trace,
        }

    # Sort years ascending
    sorted_years = sorted(metrics_by_year.keys())
    num_years = len(sorted_years) - 1  # Periods between data points

    # ── Revenue CAGR ──────────────────────────────────────────────────────
    revenues = _extract_series(metrics_by_year, sorted_years, "revenue")
    if revenues:
        trend.revenue_cagr = compute_revenue_cagr(revenues, num_years)

    # ── EBITDA trend ──────────────────────────────────────────────────────
    ebitda_series = _extract_series(metrics_by_year, sorted_years, "ebitda")
    if not ebitda_series:
        # Try profit as proxy
        ebitda_series = _extract_series(metrics_by_year, sorted_years, "profit")

    if ebitda_series and len(ebitda_series) >= 2:
        if ebitda_series[-1] > ebitda_series[0] * 1.05:
            trend.ebitda_trend = "growing"
        elif ebitda_series[-1] < ebitda_series[0] * 0.95:
            trend.ebitda_trend = "declining"
        else:
            trend.ebitda_trend = "stable"

    # ── Debt trajectory ────────────────────────────────────────────────────
    debts = _extract_series(metrics_by_year, sorted_years, "debt")
    if debts:
        growth = compute_debt_growth_rate(debts)
        trend.debt_growth_rate = growth
        if growth is not None:
            if growth > 20:
                trend.debt_trajectory = "accelerating"
            elif growth > -5:
                trend.debt_trajectory = "stable"
            else:
                trend.debt_trajectory = "decreasing"

    # ── Cash flow stability ───────────────────────────────────────────────
    cashflows = _extract_series(metrics_by_year, sorted_years, "cashflow")
    if cashflows:
        trend.cash_flow_stability = compute_cash_flow_stability(cashflows)

    # ── Profit volatility ─────────────────────────────────────────────────
    profits = _extract_series(metrics_by_year, sorted_years, "profit")
    if profits:
        trend.profit_volatility = compute_profit_volatility(profits)

    # ── Summary ────────────────────────────────────────────────────────────
    parts = []
    if trend.revenue_cagr is not None:
        parts.append(f"Revenue CAGR: {trend.revenue_cagr}%")
    if trend.ebitda_trend != "unknown":
        parts.append(f"EBITDA: {trend.ebitda_trend}")
    if trend.debt_trajectory != "unknown":
        parts.append(f"Debt: {trend.debt_trajectory}")
    trend.summary = ". ".join(parts) if parts else "No significant trends detected."

    reasoning_trace = add_reasoning_step(
        state,
        agent="trend_agent",
        decision=f"Trend analysis over {num_years} years: {trend.summary}",
        evidence=f"Years: {sorted_years}",
    )

    logger.info(f"TREND AGENT: Complete — {trend.summary}")

    return {
        **state,
        "trend_analysis": trend.model_dump(),
        "current_agent": "trend_agent",
        "reasoning_trace": reasoning_trace,
    }


def _extract_series(
    metrics_by_year: Dict[str, Dict[str, Any]],
    sorted_years: List[str],
    field: str,
) -> List[float]:
    """Extract a time series for a given field across sorted years."""
    values = []
    for year in sorted_years:
        val = metrics_by_year[year].get(field)
        if val is not None:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                pass
    return values
