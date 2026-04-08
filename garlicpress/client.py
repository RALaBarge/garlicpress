"""
Async LLM client.

Supports two backends:
  - Ollama native API (http://localhost:11434) — used when base_url contains
    "11434" or ends without "/v1", sends POST /api/chat with think:false to
    suppress extended thinking on qwen3/qwen2.5 models.
  - OpenAI-compatible API — used for everything else (OpenAI, Anthropic, etc.)

    text = await client.complete(model=..., max_tokens=..., system=..., messages=[...])
"""

from __future__ import annotations

import json
import logging

import httpx
import openai

logger = logging.getLogger("garlicpress.client")


def _is_ollama(base_url: str | None) -> bool:
    if base_url is None:
        return True  # default is Ollama
    return "11434" in base_url or base_url.rstrip("/").endswith("/api")


class LLMClient:
    def __init__(self, api_key: str | None, base_url: str | None) -> None:
        self._base_url = base_url or "http://localhost:11434"
        self._use_ollama = _is_ollama(base_url)
        if self._use_ollama:
            # Strip /v1 suffix if present — we'll call /api/chat directly
            self._ollama_base = self._base_url.rstrip("/")
            if self._ollama_base.endswith("/v1"):
                self._ollama_base = self._ollama_base[:-3]
            self._http = httpx.AsyncClient(timeout=300)
        else:
            self._openai = openai.AsyncOpenAI(
                api_key=api_key or "sk-placeholder",
                base_url=base_url,
            )

    async def complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict],
    ) -> str:
        if self._use_ollama:
            return await self._complete_ollama(model, max_tokens, system, messages)
        return await self._complete_openai(model, max_tokens, system, messages)

    async def _complete_ollama(
        self, model: str, max_tokens: int, system: str, messages: list[dict]
    ) -> str:
        payload = {
            "model": model,
            "think": False,   # disable extended thinking on qwen3/qwen2.5
            "stream": False,
            "options": {"num_predict": max_tokens, "num_ctx": 10240},
            "messages": [{"role": "system", "content": system}] + messages,
        }
        resp = await self._http.post(
            f"{self._ollama_base}/api/chat",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("message", {}).get("content") or "").strip()

    async def _complete_openai(
        self, model: str, max_tokens: int, system: str, messages: list[dict]
    ) -> str:
        response = await self._openai.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}] + messages,
        )
        msg = response.choices[0].message
        content = msg.content
        # Anthropic extended-thinking returns a list of content blocks
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
                for block in content
                if (isinstance(block, dict) and block.get("type") == "text")
                   or (hasattr(block, "type") and block.type == "text")
            )
        return (content or "").strip()
