"""
Fraud Detection Agent for Intelli-Credit.
Detects anomaly signals in financial data before risk scoring.
"""

import logging
from typing import Any, Dict, List

from app.models.state import FraudFlag, FraudSignals, add_reasoning_step
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)


# ─── Fraud Signal Definitions ────────────────────────────────────────────────

FRAUD_CHECKS = [
    {
        "name": "sudden_revenue_spike",
        "description": "Revenue increased >50% YoY without clear explanation",
        "severity": "high",
        "weight": 3.0,
    },
    {
        "name": "rapid_debt_increase",
        "description": "Total debt increased >40% YoY",
        "severity": "high",
        "weight": 2.5,
    },
    {
        "name": "negative_ocf_positive_profit",
        "description": "Negative operating cash flow despite reported positive profit",
        "severity": "high",
        "weight": 3.0,
    },
    {
        "name": "litigation_spike",
        "description": "High number of litigation mentions (>5)",
        "severity": "medium",
        "weight": 2.0,
    },
    {
        "name": "very_high_leverage",
        "description": "Debt-to-Equity ratio exceeds 4.0",
        "severity": "medium",
        "weight": 2.0,
    },
    {
        "name": "negative_net_worth",
        "description": "Total equity is negative",
        "severity": "high",
        "weight": 3.5,
    },
    {
        "name": "declining_margins_rising_revenue",
        "description": "Revenue growing but profit margins declining — potential quality issues",
        "severity": "medium",
        "weight": 1.5,
    },
]


@track_agent(timeout=30)
async def fraud_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fraud Detection Agent: Check for financial anomalies.

    Input: financial_metrics, extracted_financials, research_signals
    Output: FraudSignals stored in state
    """
    logger.info("FRAUD AGENT: Running anomaly detection")

    financial_metrics = state.get("financial_metrics", {})
    extracted_financials = state.get("extracted_financials", {})
    metrics_by_year = extracted_financials.get("metrics_by_year", {})
    research_signals = state.get("research_signals", {})

    flags: List[FraudFlag] = []

    # Sort years for trend analysis
    sorted_years = sorted(metrics_by_year.keys())

    # ── Check 1: Sudden revenue spike ─────────────────────────────────────
    if len(sorted_years) >= 2:
        latest = metrics_by_year.get(sorted_years[-1], {})
        prev = metrics_by_year.get(sorted_years[-2], {})

        rev_latest = latest.get("revenue")
        rev_prev = prev.get("revenue")
        if rev_latest and rev_prev and rev_prev > 0:
            growth = ((rev_latest - rev_prev) / abs(rev_prev)) * 100
            if growth > 50:
                flags.append(FraudFlag(
                    signal=f"Revenue spike: {growth:.0f}% YoY increase",
                    severity="high",
                    evidence=f"{sorted_years[-2]}: {rev_prev:,.0f} → {sorted_years[-1]}: {rev_latest:,.0f}",
                    weight=3.0,
                ))

    # ── Check 2: Rapid debt increase ──────────────────────────────────────
    if len(sorted_years) >= 2:
        latest = metrics_by_year.get(sorted_years[-1], {})
        prev = metrics_by_year.get(sorted_years[-2], {})

        debt_latest = latest.get("debt")
        debt_prev = prev.get("debt")
        if debt_latest and debt_prev and debt_prev > 0:
            growth = ((debt_latest - debt_prev) / abs(debt_prev)) * 100
            if growth > 40:
                flags.append(FraudFlag(
                    signal=f"Rapid debt increase: {growth:.0f}% YoY",
                    severity="high",
                    evidence=f"Debt: {debt_prev:,.0f} → {debt_latest:,.0f}",
                    weight=2.5,
                ))

    # ── Check 3: Negative OCF with positive profit ────────────────────────
    cashflow = financial_metrics.get("cashflow")
    profit = financial_metrics.get("profit")
    if cashflow is not None and profit is not None:
        if cashflow < 0 and profit > 0:
            flags.append(FraudFlag(
                signal="Negative operating cash flow despite positive profit",
                severity="high",
                evidence=f"Profit: {profit:,.0f}, Cash flow: {cashflow:,.0f}",
                weight=3.0,
            ))

    # ── Check 4: Litigation spike ─────────────────────────────────────────
    litigation = financial_metrics.get("litigation_mentions", 0)
    if isinstance(litigation, (int, float)) and litigation > 5:
        flags.append(FraudFlag(
            signal=f"High litigation mentions: {int(litigation)}",
            severity="medium",
            evidence=f"{int(litigation)} references to litigation/legal proceedings",
            weight=2.0,
        ))

    # ── Check 5: Very high leverage ───────────────────────────────────────
    dte = financial_metrics.get("debt_to_equity_ratio")
    if dte is not None and dte > 4.0:
        flags.append(FraudFlag(
            signal=f"Extremely high leverage: D/E = {dte}",
            severity="medium",
            evidence=f"Debt-to-Equity ratio of {dte} exceeds safe threshold",
            weight=2.0,
        ))

    # ── Check 6: Negative net worth ───────────────────────────────────────
    equity = financial_metrics.get("total_equity")
    if equity is not None and equity < 0:
        flags.append(FraudFlag(
            signal="Negative net worth / shareholder equity",
            severity="high",
            evidence=f"Total equity: {equity:,.0f}",
            weight=3.5,
        ))

    # ── Check 7: Declining margins with rising revenue ────────────────────
    if len(sorted_years) >= 2:
        latest = metrics_by_year.get(sorted_years[-1], {})
        prev = metrics_by_year.get(sorted_years[-2], {})

        margin_latest = latest.get("net_profit_margin")
        margin_prev = prev.get("net_profit_margin")
        rev_latest = latest.get("revenue")
        rev_prev = prev.get("revenue")

        if (margin_latest is not None and margin_prev is not None and
                rev_latest is not None and rev_prev is not None):
            if rev_latest > rev_prev and margin_latest < margin_prev - 2:
                flags.append(FraudFlag(
                    signal="Declining margins despite revenue growth",
                    severity="medium",
                    evidence=f"Margin {margin_prev:.1f}% → {margin_latest:.1f}%, Revenue grew",
                    weight=1.5,
                ))

    # ── Compute composite fraud score ─────────────────────────────────────
    if flags:
        total_weight = sum(f.weight for f in flags)
        max_possible = sum(c["weight"] for c in FRAUD_CHECKS)
        fraud_score = min(100, (total_weight / max_possible) * 100)
    else:
        fraud_score = 0.0

    fraud_signals = FraudSignals(
        flags=flags,
        fraud_score=round(fraud_score, 1),
        summary=f"{len(flags)} fraud signals detected, score: {fraud_score:.1f}/100"
        if flags else "No fraud signals detected",
    )

    reasoning_trace = add_reasoning_step(
        state,
        agent="fraud_agent",
        decision=f"Fraud score: {fraud_score:.1f}/100, {len(flags)} flags",
        evidence="; ".join(f.signal for f in flags) if flags else "Clean",
    )

    logger.info(f"FRAUD AGENT: Complete — {fraud_signals.summary}")

    return {
        **state,
        "fraud_signals": fraud_signals.model_dump(),
        "current_agent": "fraud_agent",
        "reasoning_trace": reasoning_trace,
    }
