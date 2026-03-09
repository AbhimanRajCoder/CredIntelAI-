"""
Table-to-Metrics Converter for Intelli-Credit.
Converts extracted tables into structured financial metrics using
deterministic keyword matching and Indian unit normalization.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.utils.normalizer import normalize_indian_amount, parse_fiscal_year

logger = logging.getLogger(__name__)


# ─── Metric Field Mappings ───────────────────────────────────────────────────

METRIC_KEYWORDS = {
    "revenue": [
        "revenue from operations",
        "net sales",
        "total income",
        "total revenue",
        "gross revenue",
        "income from operations",
        "net revenue",
        "sales",
    ],
    "profit": [
        "profit after tax",
        "net profit",
        "pat",
        "profit for the year",
        "profit for the period",
        "profit/(loss) for the year",
        "net income",
        "total comprehensive income",
    ],
    "ebitda": [
        "ebitda",
        "earnings before interest",
        "operating profit",
        "profit before interest and depreciation",
    ],
    "debt": [
        "total borrowings",
        "long term borrowings",
        "total debt",
        "long-term debt",
        "secured loans",
        "unsecured loans",
        "total liabilities",
    ],
    "total_equity": [
        "total equity",
        "shareholders' funds",
        "shareholder's funds",
        "shareholders fund",
        "net worth",
        "total shareholders equity",
    ],
    "total_assets": [
        "total assets",
    ],
    "current_assets": [
        "total current assets",
        "current assets",
    ],
    "current_liabilities": [
        "total current liabilities",
        "current liabilities",
    ],
    "cashflow": [
        "cash and cash equivalents at end",
        "net cash from operating",
        "cash flow from operations",
        "cash generated from operations",
    ],
    "interest_expense": [
        "finance costs",
        "interest expense",
        "interest and finance",
        "finance charges",
    ],
    "depreciation": [
        "depreciation and amortisation",
        "depreciation and amortization",
        "depreciation",
    ],
    "ebit": [
        "earnings before interest and tax",
        "ebit",
        "profit before interest and tax",
    ],
    "bank_loans": [
        "bank borrowings",
        "bank loans",
        "term loans from banks",
    ],
    "tax_expense": [
        "tax expense",
        "income tax",
        "provision for tax",
        "current tax",
    ],
}


# ─── Table Type Detection ─────────────────────────────────────────────────────

def _detect_table_type(headers: List[str], row_labels: List[str]) -> str:
    """
    Detect whether a table is Balance Sheet, P&L, Cash Flow, etc.

    Returns: balance_sheet | pnl | cash_flow | unknown
    """
    all_text = " ".join(headers + row_labels).lower()

    pnl_signals = sum(1 for kw in [
        "revenue", "profit", "loss", "income", "expense",
        "sales", "ebitda", "tax", "depreciation",
    ] if kw in all_text)

    bs_signals = sum(1 for kw in [
        "assets", "liabilities", "equity", "borrowings",
        "reserves", "capital", "shareholders",
    ] if kw in all_text)

    cf_signals = sum(1 for kw in [
        "cash flow", "cash from", "cash generated",
        "financing activities", "investing activities",
    ] if kw in all_text)

    scores = {"pnl": pnl_signals, "balance_sheet": bs_signals, "cash_flow": cf_signals}
    best = max(scores, key=scores.get)

    if scores[best] >= 2:
        return best
    return "unknown"


# ─── Year Column Detection ────────────────────────────────────────────────────

def _detect_year_columns(headers: List[str]) -> Dict[int, str]:
    """
    Detect which columns correspond to which fiscal year.

    Returns: {column_index: "FY2024", ...}
    """
    year_cols = {}

    for idx, header in enumerate(headers):
        fy = parse_fiscal_year(header)
        if fy:
            year_cols[idx] = fy

    return year_cols


# ─── Row Matching ─────────────────────────────────────────────────────────────

def _match_row_to_metric(label: str) -> Optional[str]:
    """
    Match a table row label to a financial metric field.

    Returns: metric field name or None
    """
    label_lower = label.lower().strip()

    # Remove common prefixes
    label_lower = re.sub(r"^[a-z0-9ivx]+[\.\)]\s*", "", label_lower)

    for field, keywords in METRIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in label_lower:
                return field

    return None


# ─── Main Converter ───────────────────────────────────────────────────────────

def tables_to_metrics(
    tables: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Convert reconstructed tables into structured financial metrics by year.

    Args:
        tables: List of table dicts from document parser, each with:
            - headers: List[str]
            - rows: List[List[str]]  (first element is label, rest are values)
            - page_num: int

    Returns:
        Dict of {fiscal_year: {metric: value, ...}}
        Example: {"FY2024": {"revenue": 12500000000, "profit": 500000000}, ...}
    """
    metrics_by_year: Dict[str, Dict[str, Any]] = {}
    tables_processed = 0

    for table in tables:
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        if not headers or not rows:
            continue

        # Detect fiscal year columns
        year_cols = _detect_year_columns(headers)

        if not year_cols:
            # Try first row as headers if current headers don't have years
            if rows and len(rows) > 0:
                year_cols = _detect_year_columns(rows[0])
                if year_cols:
                    rows = rows[1:]  # Skip first row since it was headers

        if not year_cols:
            # Assign generic column labels
            for idx in range(1, len(headers)):
                year_cols[idx] = f"Col{idx}"

        # Detect table type for logging
        row_labels = [row[0] if row else "" for row in rows]
        table_type = _detect_table_type(headers, row_labels)

        logger.debug(f"Processing {table_type} table with {len(rows)} rows, years: {list(year_cols.values())}")

        # Extract metrics from each row
        for row in rows:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).strip()
            metric_field = _match_row_to_metric(label)

            if not metric_field:
                continue

            # Extract values for each year column
            for col_idx, fiscal_year in year_cols.items():
                if col_idx >= len(row):
                    continue

                raw_value = str(row[col_idx]).strip()
                if not raw_value or raw_value in ("-", "--", "—"):
                    continue

                parsed = normalize_indian_amount(raw_value)
                if parsed is not None:
                    if fiscal_year not in metrics_by_year:
                        metrics_by_year[fiscal_year] = {}

                    # Don't overwrite if a more specific match already exists
                    if metric_field not in metrics_by_year[fiscal_year]:
                        metrics_by_year[fiscal_year][metric_field] = parsed

        tables_processed += 1

    logger.info(
        f"Converted {tables_processed} tables → "
        f"metrics for {len(metrics_by_year)} fiscal years: "
        f"{list(metrics_by_year.keys())}"
    )

    return metrics_by_year


def compute_derived_metrics(
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute derived financial ratios from raw metrics.

    Adds: debt_to_equity_ratio, current_ratio, interest_coverage_ratio,
          net_profit_margin, return_on_equity
    """
    result = dict(metrics)

    # Debt-to-Equity
    debt = metrics.get("debt") or metrics.get("total_debt")
    equity = metrics.get("total_equity")
    if debt is not None and equity and equity != 0:
        result["debt_to_equity_ratio"] = round(debt / equity, 2)

    # Current Ratio
    ca = metrics.get("current_assets")
    cl = metrics.get("current_liabilities")
    if ca is not None and cl and cl != 0:
        result["current_ratio"] = round(ca / cl, 2)

    # Interest Coverage
    ebit = metrics.get("ebit")
    if ebit is None:
        # Try to compute EBIT from profit + interest + tax
        profit = metrics.get("profit")
        interest = metrics.get("interest_expense")
        tax = metrics.get("tax_expense")
        if profit is not None and interest is not None:
            ebit = profit + interest + (tax or 0)

    interest = metrics.get("interest_expense")
    if ebit is not None and interest and interest != 0:
        result["interest_coverage_ratio"] = round(ebit / interest, 2)

    # Net Profit Margin
    profit = metrics.get("profit")
    revenue = metrics.get("revenue")
    if profit is not None and revenue and revenue != 0:
        result["net_profit_margin"] = round((profit / revenue) * 100, 2)

    # Return on Equity
    if profit is not None and equity and equity != 0:
        result["return_on_equity"] = round((profit / equity) * 100, 2)

    return result


def get_latest_year_metrics(
    metrics_by_year: Dict[str, Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Get the most recent fiscal year's metrics.

    Returns: (fiscal_year, metrics_dict)
    """
    if not metrics_by_year:
        return ("", {})

    # Sort by year string descending
    sorted_years = sorted(metrics_by_year.keys(), reverse=True)
    latest = sorted_years[0]
    return (latest, metrics_by_year[latest])
