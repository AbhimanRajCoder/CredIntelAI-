"""
Promoter Intelligence Module for corporate research.
Analyzes promoter background, controversies, and reputation.
"""

import logging
from typing import List, Dict, Any

from app.services.groq_client import get_groq_client
from app.models.schemas import PromoterProfile
from app.utils.prompts import PROMOTER_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


async def analyze_promoter(
    promoter_snippets: List[str],
    company_name: str,
) -> PromoterProfile:
    """
    Analyze promoter background using LLM.

    Returns a PromoterProfile Pydantic model.
    """
    if not promoter_snippets:
        logger.warning(f"No promoter data available for '{company_name}'")
        return PromoterProfile(
            risk_level="unknown",
            summary="Insufficient data available for promoter background analysis.",
        )

    data_text = "\n".join(f"- {s}" for s in promoter_snippets[:20])

    groq = get_groq_client()
    prompt = PROMOTER_ANALYSIS_PROMPT.format(
        company_name=company_name,
        snippets=data_text,
    )

    try:
        result = await groq.generate_json(
            prompt=prompt,
            system_message="You are a corporate due diligence specialist. Always respond in valid JSON.",
        )

        score = float(result.get("promoter_reputation_score", 50))
        score = max(0, min(100, score))

        profile = PromoterProfile(
            promoter_reputation_score=score,
            controversies=result.get("controversies", [])[:10],
            previous_companies=result.get("previous_companies", [])[:10],
            risk_level=result.get("risk_level", "unknown"),
            summary=result.get("summary", ""),
        )

        logger.info(
            f"Promoter analysis for '{company_name}': "
            f"score={profile.promoter_reputation_score}, risk={profile.risk_level}"
        )
        return profile

    except Exception as e:
        logger.error(f"Promoter analysis failed: {e}")
        return PromoterProfile(
            risk_level="unknown",
            summary=f"Promoter analysis could not be completed: {str(e)}",
        )
