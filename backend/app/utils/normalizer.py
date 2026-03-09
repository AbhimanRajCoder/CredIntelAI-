"""
Indian Financial Unit Normalizer for Intelli-Credit.
Converts Indian currency notations (Cr, Lakhs, Mn, etc.) to raw numeric values.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Unit Multipliers ─────────────────────────────────────────────────────────

UNIT_MULTIPLIERS = {
    # Crores
    "cr": 1e7,
    "crore": 1e7,
    "crores": 1e7,
    "cr.": 1e7,
    # Lakhs
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "l": 1e5,
    # Thousands
    "k": 1e3,
    "thousand": 1e3,
    "thousands": 1e3,
    # Millions
    "mn": 1e6,
    "m": 1e6,
    "million": 1e6,
    "millions": 1e6,
    "mil": 1e6,
    # Billions
    "bn": 1e9,
    "b": 1e9,
    "billion": 1e9,
    "billions": 1e9,
    # Trillions
    "tn": 1e12,
    "trillion": 1e12,
    "trillions": 1e12,
}


def normalize_indian_amount(value: str) -> Optional[float]:
    """
    Convert Indian financial notation to raw float.

    Examples:
        "₹1,250 Cr"      → 12500000000.0
        "45.2 Lakhs"      → 4520000.0
        "₹3.5 Mn"         → 3500000.0
        "(2,100)"         → -2100.0
        "1,23,456"        → 123456.0
        "-5,000.50"       → -5000.5
        "Rs. 42 Crore"    → 420000000.0
        "NIL"             → 0.0
        "N/A"             → None

    Args:
        value: String representation of the amount

    Returns:
        Float value or None if unparseable
    """
    if value is None:
        return None

    original = str(value).strip()

    if not original:
        return None

    # Handle explicit null-like values
    lower = original.lower()
    if lower in ("nil", "null", "-", "--", "—", "n.a.", "n.a", "na"):
        return 0.0
    if lower in ("n/a", "not available", "not applicable", "none", ""):
        return None

    # Detect negative from parentheses: (1,200) → -1200
    is_negative = False
    cleaned = original

    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()

    # Remove currency symbols and common prefixes
    cleaned = re.sub(r"[₹$€£¥]", "", cleaned)
    cleaned = re.sub(r"(?i)^(rs\.?|inr|usd|eur)\s*", "", cleaned).strip()

    # Check for negative sign
    if cleaned.startswith("-"):
        is_negative = True
        cleaned = cleaned[1:].strip()

    # Extract number and unit
    # Pattern: optional number followed by optional unit
    match = re.match(
        r"^([0-9][0-9,]*\.?[0-9]*)\s*([a-zA-Z.]*)\s*$",
        cleaned,
    )

    if not match:
        # Try to extract just digits
        digits_match = re.search(r"([0-9][0-9,]*\.?[0-9]*)", cleaned)
        if digits_match:
            number_str = digits_match.group(1)
            # Find unit after the number
            remaining = cleaned[digits_match.end():].strip().lower().rstrip(".")
            unit = remaining if remaining else ""
        else:
            logger.debug(f"Could not parse amount: '{original}'")
            return None
    else:
        number_str = match.group(1)
        unit = match.group(2).strip().lower().rstrip(".")

    # Remove commas (handles both 1,000 and 1,23,456 Indian notation)
    number_str = number_str.replace(",", "")

    try:
        numeric = float(number_str)
    except ValueError:
        logger.debug(f"Could not convert to float: '{number_str}' from '{original}'")
        return None

    # Apply unit multiplier
    if unit:
        multiplier = UNIT_MULTIPLIERS.get(unit)
        if multiplier:
            numeric *= multiplier
        else:
            logger.debug(f"Unknown unit '{unit}' in '{original}', treating as raw number")

    # Apply negative
    if is_negative:
        numeric = -numeric

    return numeric


def normalize_percentage(value: str) -> Optional[float]:
    """
    Normalize percentage value.

    Examples:
        "15.5%"  → 15.5
        "0.155"  → 15.5  (if clearly a decimal ratio)
        "-3.2%"  → -3.2
    """
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    # Remove % sign
    has_percent = "%" in cleaned
    cleaned = cleaned.replace("%", "").strip()

    try:
        result = float(cleaned)
    except ValueError:
        return None

    # If no % sign and value is between -1 and 1, likely a ratio
    if not has_percent and -1 <= result <= 1 and result != 0:
        result *= 100

    return result


def parse_fiscal_year(text: str) -> Optional[str]:
    """
    Extract fiscal year from text.

    Examples:
        "FY2024"     → "FY2024"
        "FY 2023-24" → "FY2024"
        "2023-24"    → "FY2024"
        "2024"       → "FY2024"
        "Mar 2024"   → "FY2024"
    """
    if not text:
        return None

    cleaned = text.strip().upper()

    # Match FY2024 or FY 2024
    m = re.match(r"FY\s*(\d{4})", cleaned)
    if m:
        return f"FY{m.group(1)}"

    # Match FY2023-24 or FY 2023-24
    m = re.match(r"FY\s*(\d{4})\s*[-–]\s*(\d{2,4})", cleaned)
    if m:
        end_year = m.group(2)
        if len(end_year) == 2:
            end_year = m.group(1)[:2] + end_year
        return f"FY{end_year}"

    # Match 2023-24
    m = re.match(r"(\d{4})\s*[-–]\s*(\d{2,4})", cleaned)
    if m:
        end_year = m.group(2)
        if len(end_year) == 2:
            end_year = m.group(1)[:2] + end_year
        return f"FY{end_year}"

    # Match bare 4-digit year
    m = re.match(r"(\d{4})$", cleaned)
    if m:
        return f"FY{m.group(1)}"

    return None
