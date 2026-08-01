"""
LocalBrain — the ONLY inference backend.

It talks to a local Ollama server (default http://127.0.0.1:11434) for BOTH:
  * reasoning / chat  (settings.brain_model, e.g. llava:7b)
  * embeddings        (settings.embedding_model, e.g. nomic-embed-text)

There is deliberately NO OpenAI / Claude / Gemini / cloud path. Nothing you
say ever leaves this machine. If you later fine-tune your own model, point
BRAIN_MODEL at it and everything else keeps working unchanged.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger("sexta-feira.brain")


class BrainUnavailable(RuntimeError):
    """Raised when the local Ollama server can't be reached."""


class LocalBrain:
    """Async client for local Ollama inference (chat + embeddings)."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
    ):
        self.endpoint = (endpoint or settings.ollama_endpoint).rstrip("/")
        self.model = model or settings.brain_model
        self.embedding_model = embedding_model or settings.embedding_model
        # One shared client => connection pooling / keep-alive (no per-request TLS churn).
        self._client = httpx.AsyncClient(base_url=self.endpoint, timeout=httpx.Timeout(300.0))  # 5min for llava:7b cold start
        logger.info("LocalBrain wired to %s (model=%s, embed=%s)",
                    self.endpoint, self.model, self.embedding_model)

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------- health ----------

    async def health(self) -> bool:
        try:
            r = await self._client.get("/api/tags", timeout=5.0)
            return r.status_code == 200
        except Exception as e:  # noqa: BLE001
            logger.warning("Brain health check failed: %s", e)
            return False

    async def installed_models(self) -> list[str]:
        try:
            r = await self._client.get("/api/tags", timeout=5.0)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:  # noqa: BLE001
            return []

    # ---------- chat ----------

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Non-streaming completion. `messages` = [{"role","content"}...]."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": settings.brain_temperature if temperature is None else temperature,
                "num_predict": settings.brain_max_tokens if max_tokens is None else max_tokens,
            },
        }
        try:
            r = await self._client.post("/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise BrainUnavailable(
                f"Ollama não respondeu em {self.endpoint}. "
                f"Rode `ollama serve` e `ollama pull {self.model}`."
            ) from e

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """
        Tool-calling completion. Returns the full Ollama `message` dict, which may
        contain `tool_calls` when the model decides to act. Models that don't
        support tools simply return normal content — the caller handles both.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": settings.brain_temperature if temperature is None else temperature,
                "num_predict": settings.brain_max_tokens if max_tokens is None else max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools
        try:
            r = await self._client.post("/api/chat", json=payload)
            r.raise_for_status()
            return r.json().get("message", {"role": "assistant", "content": ""})
        except httpx.ConnectError as e:
            raise BrainUnavailable(
                f"Ollama não respondeu em {self.endpoint}. Rode `ollama serve`."
            ) from e

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Token-by-token streaming completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": settings.brain_temperature if temperature is None else temperature,
                "num_predict": settings.brain_max_tokens if max_tokens is None else max_tokens,
            },
        }
        import json as _json
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = _json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
        except httpx.ConnectError as e:
            raise BrainUnavailable(
                f"Ollama não respondeu em {self.endpoint}. Rode `ollama serve`."
            ) from e

    # ---------- embeddings ----------

    async def embed(self, text: str) -> list[float]:
        """Locally compute an embedding vector for `text`."""
        try:
            r = await self._client.post(
                "/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=30.0,
            )
            r.raise_for_status()
            return r.json().get("embedding", [])
        except httpx.ConnectError as e:
            raise BrainUnavailable(
                f"Ollama não respondeu em {self.endpoint}. "
                f"Rode `ollama pull {self.embedding_model}`."
            ) from e
