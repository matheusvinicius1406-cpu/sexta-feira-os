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
        # None until a tool-calling request has been tried. See chat_with_tools:
        # Ollama answers 400 for a model without tool support, so this is learned
        # from one rejection rather than assumed.
        self._supports_tools: bool | None = None
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
        contain `tool_calls` when the model decides to act.

        A model without tool support does NOT "simply return normal content", as
        this docstring used to claim. Ollama rejects the request outright:

            400  {"error": "... llava:7b does not support tools"}

        which `raise_for_status` turned into an unhandled HTTPStatusError and a
        500 on /chat. With llava:7b as the sole brain — it is a vision model, and
        reports capabilities ["completion", "vision"] — that made every chat
        request fail. So the fallback is real: drop the tools and ask again. The
        assistant answers without being able to act, which is the honest
        degradation, and the finding is remembered so the failed request is paid
        for once per process rather than on every message.
        """
        use_tools = bool(tools) and self._supports_tools is not False
        message = await self._post_chat(messages, tools if use_tools else None,
                                        temperature, max_tokens)
        if message is not None:
            if use_tools:
                self._supports_tools = True
            return message

        # Only reachable when the model rejected the tools themselves.
        self._supports_tools = False
        logger.warning(
            "%s não suporta tool-calling; respondendo sem ferramentas. "
            "Para que o Jarvis possa agir, use um modelo com 'tools' "
            "(ex.: qwen2.5, llama3.1) em BRAIN_MODEL.",
            self.model,
        )
        message = await self._post_chat(messages, None, temperature, max_tokens)
        if message is None:
            # Refused without tools too — that is not the tools' fault.
            raise BrainUnavailable(f"{self.model} recusou a requisição de chat.")
        return message

    async def _post_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict | None:
        """One /api/chat call. `None` means "this model refuses tools"."""
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
            if r.status_code == 400 and "does not support tools" in r.text:
                return None
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
