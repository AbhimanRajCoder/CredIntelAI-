"""
Document Section Detector for Intelli-Credit.
Identifies financial document sections (Balance Sheet, P&L, Cash Flow, etc.)
from OCR/digital text using keyword matching and layout heuristics.
"""

import re
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ─── Section Types ────────────────────────────────────────────────────────────

class DetectedSection(BaseModel):
    """A detected section in a financial document."""
    section_type: str = Field(..., description="balance_sheet | pnl | cash_flow | auditor_report | notes_to_accounts | directors_report | management_discussion | schedules | other")
    start_page: int = Field(0, description="Page where section starts (0-indexed)")
    end_page: Optional[int] = Field(None, description="Page where section ends")
    confidence: float = Field(0.0, ge=0, le=1.0, description="Detection confidence")
    heading_text: str = Field("", description="Matched heading text")


# ─── Keyword Patterns ─────────────────────────────────────────────────────────

SECTION_PATTERNS = {
    "balance_sheet": [
        r"balance\s+sheet",
        r"statement\s+of\s+financial\s+position",
        r"consolidated\s+balance\s+sheet",
        r"standalone\s+balance\s+sheet",
    ],
    "pnl": [
        r"profit\s+and\s+loss",
        r"statement\s+of\s+profit",
        r"income\s+statement",
        r"statement\s+of\s+comprehensive\s+income",
        r"statement\s+of\s+operations",
        r"revenue\s+account",
    ],
    "cash_flow": [
        r"cash\s+flow\s+statement",
        r"statement\s+of\s+cash\s+flows",
        r"cash\s+flow\s+from\s+operations",
    ],
    "auditor_report": [
        r"independent\s+auditor",
        r"auditor['']?s?\s+report",
        r"statutory\s+auditor",
        r"audit\s+report",
    ],
    "notes_to_accounts": [
        r"notes\s+to\s+financial",
        r"notes\s+forming\s+part",
        r"notes\s+to\s+accounts",
        r"significant\s+accounting\s+policies",
    ],
    "directors_report": [
        r"director['']?s?\s+report",
        r"board['']?s?\s+report",
        r"report\s+of\s+the\s+board",
    ],
    "management_discussion": [
        r"management\s+discussion",
        r"management\s+commentary",
        r"md\s*&\s*a",
        r"management['']?s?\s+discussion\s+and\s+analysis",
    ],
    "schedules": [
        r"schedule\s+[a-z0-9ivx]+",
        r"annexure",
    ],
}


def detect_sections_from_text(
    page_texts: List[str],
) -> List[DetectedSection]:
    """
    Detect document sections from a list of page texts.

    Args:
        page_texts: List of text content, one per page (0-indexed)

    Returns:
        List of DetectedSection objects
    """
    sections: List[DetectedSection] = []
    seen_types = set()

    for page_idx, text in enumerate(page_texts):
        if not text:
            continue

        # Check first ~500 chars and headings for section markers
        # Headings are typically ALL-CAPS lines or short lines
        lines = text.split("\n")

        for line in lines[:30]:  # Check first 30 lines of each page
            clean_line = line.strip()
            if not clean_line or len(clean_line) < 5:
                continue

            line_lower = clean_line.lower()

            for section_type, patterns in SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower):
                        # Calculate confidence based on context
                        confidence = _compute_confidence(clean_line, section_type)

                        # Avoid duplicate detections (use first occurrence)
                        section_key = f"{section_type}_{page_idx}"
                        if section_key not in seen_types:
                            seen_types.add(section_key)
                            sections.append(DetectedSection(
                                section_type=section_type,
                                start_page=page_idx,
                                confidence=confidence,
                                heading_text=clean_line[:100],
                            ))
                        break  # Found match for this line, skip other patterns
                else:
                    continue
                break  # Found match for this line, skip other section types

    # Sort by page number
    sections.sort(key=lambda s: s.start_page)

    # Infer end pages
    for i, section in enumerate(sections):
        if i + 1 < len(sections):
            section.end_page = sections[i + 1].start_page - 1
        else:
            section.end_page = len(page_texts) - 1

    logger.info(
        f"Detected {len(sections)} sections: "
        f"{[s.section_type for s in sections]}"
    )

    return sections


def _compute_confidence(heading_text: str, section_type: str) -> float:
    """Compute confidence score for a section detection."""
    confidence = 0.6  # Base confidence for keyword match

    # Higher confidence for ALL-CAPS headings
    if heading_text.isupper():
        confidence += 0.2

    # Higher confidence for short headings (likely standalone)
    if len(heading_text) < 60:
        confidence += 0.1

    # Higher confidence for common financial sections
    if section_type in ("balance_sheet", "pnl", "cash_flow"):
        confidence += 0.1

    return min(confidence, 1.0)


def get_section_for_page(
    sections: List[DetectedSection], page_num: int
) -> Optional[str]:
    """Get the section type for a given page number."""
    for section in sections:
        end = section.end_page if section.end_page is not None else float("inf")
        if section.start_page <= page_num <= end:
            return section.section_type
    return None


def get_detected_section_types(sections: List[DetectedSection]) -> List[str]:
    """Get unique list of detected section types."""
    return list(dict.fromkeys(s.section_type for s in sections))
