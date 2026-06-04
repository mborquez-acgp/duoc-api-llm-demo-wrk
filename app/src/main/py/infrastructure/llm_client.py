import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            logger.warning("Gemini request skipped because API key is not configured")
            raise RuntimeError("LLM_API_KEY is not configured")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            logger.info("calling Gemini API model=%s prompt_chars=%s", self.model, len(prompt))
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.warning("Gemini API returned error status=%s detail=%s", exc.code, detail)
            raise RuntimeError(f"Gemini API error {exc.code}: {detail}") from exc
        except URLError as exc:
            logger.warning("Gemini API connection failed reason=%s", exc.reason)
            raise RuntimeError(f"Could not reach Gemini API: {exc.reason}") from exc

        text = self._extract_text(data)
        logger.info("Gemini API response received model=%s response_chars=%s", self.model, len(text))
        return text

    def _extract_text(self, data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning("Gemini API response did not include candidates")
            raise RuntimeError("Gemini API did not return candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if part.get("text")]
        if not texts:
            logger.warning("Gemini API response did not include text")
            raise RuntimeError("Gemini API did not return text")
        return "\n".join(texts)
