"""
Intelligent Query Generator for corporate research.
Generates 10-15 targeted search queries based on company, sector, and promoter info.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def generate_research_queries(
    company_name: str,
    sector: str,
    promoter_names: Optional[List[str]] = None,
) -> dict:
    """
    Generate categorized search queries for comprehensive company research.

    Returns dict with categories: litigation, promoter, sector, financial, regulatory
    """
    queries = {
        "litigation": [
            f"{company_name} litigation case India",
            f"{company_name} NCLT filing",
            f"{company_name} fraud investigation",
            f"{company_name} court dispute penalty",
        ],
        "promoter": [
            f"{company_name} promoter background",
            f"{company_name} promoter controversy",
            f"{company_name} directors board members",
        ],
        "sector": [
            f"{sector} industry outlook India 2024 2025",
            f"{sector} regulatory risk India RBI",
            f"{sector} growth forecast India",
        ],
        "financial": [
            f"{company_name} financial results news",
            f"{company_name} debt restructuring",
            f"{company_name} credit rating",
        ],
        "regulatory": [
            f"{company_name} RBI penalty",
            f"{company_name} SEBI investigation",
            f"{company_name} regulatory compliance India",
        ],
    }

    # Add promoter-specific queries if names are provided
    if promoter_names:
        for name in promoter_names[:3]:  # Limit to top 3
            queries["promoter"].append(f"{name} business profile India")
            queries["promoter"].append(f"{name} controversy litigation fraud")
            queries["promoter"].append(f"{name} SEBI debarment order")
            queries["promoter"].append(f"{name} criminal record India")
            queries["promoter"].append(f"{name} wilfull defaulter list")

    total = sum(len(v) for v in queries.values())
    logger.info(f"Generated {total} research queries for '{company_name}' in '{sector}'")

    return queries


def flatten_queries(categorized: dict) -> List[str]:
    """Flatten categorized queries into a single list."""
    flat = []
    for category_queries in categorized.values():
        flat.extend(category_queries)
    return flat
