"""
Sector Intelligence Module for corporate research.
Analyzes industry outlook, regulatory risks, and market trends.
"""

import logging
from typing import List

from app.services.groq_client import get_groq_client
from app.models.schemas import SectorIntelligence
from app.utils.prompts import SECTOR_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


async def analyze_sector(
    sector_snippets: List[str],
    sector: str,
) -> SectorIntelligence:
    """
    Analyze sector outlook using LLM.

    Returns a SectorIntelligence Pydantic model.
    """
    if not sector_snippets:
        logger.warning(f"No sector data available for '{sector}'")
        return SectorIntelligence(
            summary="Insufficient data available for sector analysis.",
        )

    data_text = "\n".join(f"- {s}" for s in sector_snippets[:20])

    groq = get_groq_client()
    prompt = SECTOR_ANALYSIS_PROMPT.format(
        sector=sector,
        snippets=data_text,
    )

    try:
        result = await groq.generate_json(
            prompt=prompt,
            system_message="You are an industry research analyst. Always respond in valid JSON.",
        )

        intel = SectorIntelligence(
            sector_outlook=result.get("sector_outlook", "unknown"),
            regulatory_risk=result.get("regulatory_risk", "unknown"),
            industry_headwinds=result.get("industry_headwinds", [])[:8],
            industry_tailwinds=result.get("industry_tailwinds", [])[:8],
            summary=result.get("summary", ""),
        )

        logger.info(
            f"Sector analysis for '{sector}': "
            f"outlook={intel.sector_outlook}, reg_risk={intel.regulatory_risk}"
        )
        return intel

    except Exception as e:
        logger.error(f"Sector analysis failed: {e}")
        return SectorIntelligence(
            summary=f"Sector analysis could not be completed: {str(e)}",
        )
