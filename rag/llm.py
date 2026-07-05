"""Cliente HTTP mínimo para el servidor local de Ollama (self-hosted, sin costo)."""
from __future__ import annotations

import requests

from rag.config import RagConfig


class OllamaClient:
    def __init__(self, config: RagConfig):
        self._config = config

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        resp = requests.post(
            f"{self._config.ollama_host}/api/chat",
            json={
                "model": self._config.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": self._config.llm_temperature},
            },
            timeout=self._config.llm_timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
