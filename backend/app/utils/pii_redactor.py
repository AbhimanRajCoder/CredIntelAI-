"""
PII Redaction Layer for Intelli-Credit.
Regex-based redaction of PAN, Aadhaar, email, phone, and bank account numbers
before sending documents to LLMs or vector stores.
"""

import re
import logging
from typing import Dict, List, Tuple

from app.config import get_settings

logger = logging.getLogger(__name__)


# ─── Redaction Patterns ───────────────────────────────────────────────────────

PII_PATTERNS: List[Tuple[str, str, re.Pattern]] = [
    # PAN Number: ABCDE1234F (5 letters, 4 digits, 1 letter)
    (
        "PAN",
        "[PAN_REDACTED]",
        re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    ),
    # Aadhaar Number: 1234 5678 9012 or 123456789012
    (
        "AADHAAR",
        "[AADHAAR_REDACTED]",
        re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"),
    ),
    # Email addresses
    (
        "EMAIL",
        "[EMAIL_REDACTED]",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    ),
    # Indian phone numbers: +91XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX, XXXXXXXXXX
    (
        "PHONE",
        "[PHONE_REDACTED]",
        re.compile(r"(?:\+91[\s-]?|91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}\b"),
    ),
    # Bank account numbers: 8-18 digits (common range)
    (
        "BANK_ACCOUNT",
        "[BANK_ACCT_REDACTED]",
        re.compile(r"\b\d{8,18}\b"),
    ),
    # IFSC Code: 4 letters + 0 + 6 alphanum
    (
        "IFSC",
        "[IFSC_REDACTED]",
        re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    ),
]

# Patterns that should NOT be redacted (false positive guards)
FALSE_POSITIVE_GUARDS = [
    re.compile(r"^\d{4}$"),              # 4-digit year
    re.compile(r"^\d{1,3}(,\d{3})*$"),   # Comma-separated numbers (amounts)
    re.compile(r"^\d+\.\d+$"),           # Decimal numbers (ratios)
    re.compile(r"^FY\d{4}$"),            # Fiscal year
    re.compile(r"^[A-Z]{2,4}\d{5,}$"),   # Stock codes, CIN etc.
]


def redact_pii(text: str) -> str:
    """
    Redact PII from text by replacing sensitive patterns with tagged placeholders.

    Args:
        text: Input text potentially containing PII

    Returns:
        Text with PII replaced by [TYPE_REDACTED] placeholders
    """
    settings = get_settings()
    if not settings.PII_REDACTION_ENABLED:
        return text

    if not text:
        return text

    redacted = text
    total_redactions = 0

    for pii_type, replacement, pattern in PII_PATTERNS:
        matches = list(pattern.finditer(redacted))

        # Process matches in reverse to maintain correct positions
        for match in reversed(matches):
            matched_text = match.group()

            # Check false positive guards
            if _is_false_positive(matched_text, pii_type):
                continue

            redacted = redacted[:match.start()] + replacement + redacted[match.end():]
            total_redactions += 1

    if total_redactions > 0:
        logger.info(f"Redacted {total_redactions} PII instances from text")

    return redacted


def _is_false_positive(text: str, pii_type: str) -> bool:
    """Check if a match is a false positive."""
    # Bank account pattern is aggressive — add extra guards
    if pii_type == "BANK_ACCOUNT":
        # Don't redact pure financial amounts (all digits, could be revenue/profit)
        if len(text) < 10:
            return True
        # Don't redact CIN numbers or registration numbers
        for guard in FALSE_POSITIVE_GUARDS:
            if guard.match(text):
                return True

    # Phone number guards
    if pii_type == "PHONE":
        # Very short matches are likely not phone numbers
        clean = re.sub(r"[\s-]", "", text)
        if len(clean) < 10:
            return True

    return False


def get_redaction_summary(original: str, redacted: str) -> Dict[str, int]:
    """Get a summary of redactions performed."""
    summary = {}
    for pii_type, replacement, _ in PII_PATTERNS:
        count = redacted.count(replacement)
        if count > 0:
            summary[pii_type] = count
    return summary
