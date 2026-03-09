"""
Risk Signal Extractor for corporate research.
Uses Groq LLM to extract structured risk signals from article snippets.
"""

import logging
from typing import List, Dict, Any

from app.services.groq_client import get_groq_client
from app.models.schemas import RiskSignal
from app.utils.prompts import SIGNAL_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


async def extract_signals(
    snippets: List[str],
    company_name: str,
    sector: str,
) -> Dict[str, Any]:
    """
    Use LLM to extract structured risk signals from article snippets.

    Returns:
        dict with 'signals' (List[RiskSignal]), 'positive_highlights', 'negative_highlights'
    """
    if not snippets:
        return {"signals": [], "positive_highlights": [], "negative_highlights": []}

    # Limit to prevent token overflow
    trimmed = snippets[:40]
    snippets_text = "\n".join(f"[{i+1}] {s}" for i, s in enumerate(trimmed))

    groq = get_groq_client()
    prompt = SIGNAL_EXTRACTION_PROMPT.format(
        company_name=company_name,
        sector=sector,
        snippets=snippets_text,
    )

    try:
        result = await groq.generate_json(
            prompt=prompt,
            system_message="You are a corporate credit intelligence analyst. Always respond in valid JSON.",
        )

        # Parse signals into RiskSignal models
        raw_signals = result.get("signals", [])
        parsed_signals = []
        for sig in raw_signals:
            try:
                parsed_signals.append(RiskSignal(
                    type=sig.get("type", "unknown"),
                    severity=sig.get("severity", "medium"),
                    description=sig.get("description", ""),
                    source=sig.get("source"),
                    date=sig.get("date"),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse signal: {e}")

        logger.info(f"Extracted {len(parsed_signals)} risk signals for '{company_name}'")

        return {
            "signals": parsed_signals,
            "positive_highlights": result.get("positive_highlights", []),
            "negative_highlights": result.get("negative_highlights", []),
        }

    except Exception as e:
        logger.error(f"Signal extraction failed: {e}")
        return {"signals": [], "positive_highlights": [], "negative_highlights": []}
