"""
Groq LLM Client Service for Intelli-Credit.
Provides a reusable async client for LLM inference via Groq.
"""

import json
import logging
from typing import Optional, Dict, Any

from groq import Groq, AsyncGroq
from app.config import get_settings
from app.config import get_settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Reusable Groq LLM client for inference."""

    def __init__(self):
        self.settings = get_settings()
        self._sync_client: Optional[Groq] = None
        self._async_client: Optional[AsyncGroq] = None

    @property
    def sync_client(self) -> Groq:
        if self._sync_client is None:
            self._sync_client = Groq(api_key=self.settings.GROQ_API_KEY)
        return self._sync_client

    @property
    def async_client(self) -> AsyncGroq:
        if self._async_client is None:
            self._async_client = AsyncGroq(api_key=self.settings.GROQ_API_KEY)
        return self._async_client

    async def generate(
        self,
        prompt: str,
        system_message: str = "You are a helpful financial analyst assistant.",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from the Groq LLM."""
        model = model or self.settings.LLM_MODEL
        temperature = temperature if temperature is not None else self.settings.LLM_TEMPERATURE
        max_tokens = max_tokens or self.settings.LLM_MAX_TOKENS

        logger.info(f"Sending request to Groq model: {model}")

        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            result = response.choices[0].message.content
            logger.info(f"Received response from Groq ({len(result)} chars)")
            return result

        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise

    async def generate_json(
        self,
        prompt: str,
        system_message: str = "You are a helpful financial analyst. Always respond in valid JSON.",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a JSON response from the Groq LLM."""
        raw_response = await self.generate(
            prompt=prompt,
            system_message=system_message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Clean response — extract JSON from markdown code blocks if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed_json = json.loads(cleaned)
            return parsed_json
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {raw_response}")
            # Attempt to find JSON block in response
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    parsed_json = json.loads(cleaned[start:end])
                    return parsed_json
                except json.JSONDecodeError:
                    pass
            
            raise ValueError(f"Could not parse LLM response as JSON: {e}")


# Singleton instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create the Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
