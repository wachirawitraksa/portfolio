"""The only place that talks to a language model. One small interface, so another provider (Groq, ...)
can be added or swapped in without touching the rest. The API key lives here and nowhere else."""
from typing import Protocol

import httpx

from ..config import get_settings

CHEAP, SMART = "cheap", "smart"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMUnavailable(Exception):
    """No key, quota used up, timeout, provider error, or an empty reply. The caller falls back."""


class LLM(Protocol):
    async def generate(self, system: str, user: str, tier: str) -> str: ...


class Gemini:
    async def generate(self, system: str, user: str, tier: str) -> str:
        s = get_settings()
        model = s.gemini_model_smart if tier == SMART else s.gemini_model_cheap
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
        }
        try:
            async with httpx.AsyncClient(timeout=s.llm_timeout_seconds) as http:
                resp = await http.post(
                    ENDPOINT.format(model=model), json=body, headers={"x-goog-api-key": s.gemini_api_key}
                )
            if resp.status_code != 200:  # 429 is the quota; 5xx is the provider
                raise LLMUnavailable(f"gemini returned {resp.status_code}")
            parts = resp.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as error:
            raise LLMUnavailable(str(error)) from error
        if not text:
            raise LLMUnavailable("empty reply")
        return text


def get_llm() -> LLM | None:
    """None when no key is configured: the question box then runs without a model."""
    return Gemini() if get_settings().gemini_api_key else None
