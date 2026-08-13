"""
LocalBrain — the ONLY inference backend.

It talks to a local Ollama server (default http://127.0.0.1:11434) for:
  * reasoning / chat  (settings.brain_model, e.g. qwen3-vl:2b)
  * tool-calling      — the same model, deciding to act
  * seeing            — the same model, handed images inline
  * embeddings        (settings.embedding_model, e.g. nomic-embed-text)

One model does the first three. That is deliberate: a brain that can look at a
photo and then call a tool about what it saw is a different thing from a chat
model with a vision model bolted beside it, and on a box with 12 GB of RAM two
resident models mean each one evicts the other.

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


def tuned_options(**base) -> dict:
    """Ollama `options`, with the measured knobs applied when they are set.

    A zero means "not measured yet" and is left OUT of the payload entirely
    rather than sent as 0 — Ollama reads `num_thread: 0` as an instruction, not
    as an absence, and would run single-threaded on a machine nobody profiled.
    See app/brain/optimizer.py for where the non-zero values come from.
    """
    options = dict(base)
    if settings.brain_num_ctx:
        options["num_ctx"] = settings.brain_num_ctx
    if settings.brain_num_thread:
        options["num_thread"] = settings.brain_num_thread
    return options


def attach_images(messages: list[dict], images: list[str] | None) -> list[dict]:
    """Hang base64 images off the last user message, where Ollama looks for them.

    Ollama takes images per-message, not per-request, and only reads them from
    the turn being answered. Copies rather than mutates: the caller's list is
    usually the conversation history, and an image silently pinned to a stored
    turn would be re-sent on every later request in that conversation.
    """
    if not images:
        return messages
    out = [dict(m) for m in messages]
    for m in reversed(out):
        if m.get("role") == "user":
            m["images"] = list(images)
            return out
    out.append({"role": "user", "content": "", "images": list(images)})
    return out


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
        # 300 s used to be the deadline, which was BELOW the HUD's own 600 s
        # (jarvis-ui/src/arc/api.js): the kernel gave up on Ollama while the
        # browser was still willing to wait, turning a slow honest answer into
        # a 500. On this box a first photo turn measured ~277 s for a bare
        # question and more with the full prompt, so the ceiling has to sit
        # above the HUD's, not under it.
        self._client = httpx.AsyncClient(base_url=self.endpoint, timeout=httpx.Timeout(900.0))
        # What Ollama says this model can do, read once from /api/show. None
        # until asked; the empty set means "asked and could not tell".
        self._capabilities: set[str] | None = None
        # None until a tool-calling request has been tried. The capability probe
        # normally settles this first; this stays as the backstop for an Ollama
        # too old to report capabilities, which answers 400 instead.
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

    # ---------- what this model can do ----------

    async def capabilities(self) -> set[str]:
        """Ollama's own answer for this model, e.g. {completion, tools, vision, thinking}.

        `/api/show` is the only endpoint that carries this. `/api/tags` — the
        obvious place to look, and where the optimizer looked — does not return
        a `capabilities` field at all, so every check written against it was
        comparing to an empty list and quietly passing.

        An ANSWER is cached, a failure is not. Ollama returning an empty list is
        a real answer (an old build that does not report capabilities) and is
        worth keeping; a connection error is not, and caching it would leave a
        kernel that booted seconds before Ollama believing forever that its
        brain has no hands.

        Either way the empty set means "unknown", never "cannot": declining to
        send tools because a probe failed would disable a working assistant
        over a missing field.
        """
        if self._capabilities is not None:
            return self._capabilities

        try:
            r = await self._client.post("/api/show", json={"model": self.model}, timeout=30.0)
            r.raise_for_status()
            caps = {str(c).lower() for c in (r.json().get("capabilities") or [])}
        except Exception as e:  # noqa: BLE001 — never fatal; ask again next time
            logger.warning("Não deu para ler as capacidades de %s: %s", self.model, e)
            return set()

        self._capabilities = caps
        if caps:
            logger.info("%s sabe: %s", self.model, ", ".join(sorted(caps)))
            if "tools" in caps:
                self._supports_tools = True
        return caps

    async def can_see(self) -> bool:
        """Can the brain be handed an image? Unknown counts as no.

        The caller uses this to decide whether to send pixels at all, and a
        wrong yes wastes a full CPU inference on a model that will describe
        nothing. A wrong no only costs a clear error.
        """
        return "vision" in await self.capabilities()

    # ---------- chat ----------

    async def _payload(
        self,
        messages: list[dict],
        *,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        images: list[str] | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """The one place a /api/chat body is built, so every path agrees."""
        payload: dict = {
            "model": self.model,
            "messages": attach_images(messages, images),
            "stream": stream,
            "keep_alive": settings.brain_keep_alive,
            "options": tuned_options(
                temperature=settings.brain_temperature if temperature is None else temperature,
                num_predict=settings.brain_max_tokens if max_tokens is None else max_tokens,
            ),
        }
        if tools:
            payload["tools"] = tools
        # Asked of the MESSAGES, not of the `images` argument. The tool loop
        # attaches the picture to the message list once and then calls back
        # without the argument (so the image sits in a stable prefix the KV
        # cache can keep), which means keying off the argument would raise the
        # ceiling on the first round and drop it on every round after — the
        # rounds that carry MORE context, not less.
        if settings.brain_num_ctx_vision and any(m.get("images") for m in payload["messages"]):
            # Without this the picture overflows Ollama's 4096-token default and
            # the whole turn comes back 400. `max` because a measured
            # BRAIN_NUM_CTX above the floor is a real measurement, and a
            # constant must not lower it.
            payload["options"]["num_ctx"] = max(
                payload["options"].get("num_ctx", 0), settings.brain_num_ctx_vision,
            )
        # `think` is only legal on a model that reports the capability: Ollama
        # answers 400 "does not support thinking" for anything else. So an
        # unknown capability sends nothing, and the model's own default stands.
        if "thinking" in await self.capabilities():
            payload["think"] = settings.brain_thinking
        return payload

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        images: list[str] | None = None,
    ) -> str:
        """Non-streaming completion. `messages` = [{"role","content"}...].

        Routed through `_post_chat` (tools=None) rather than posting directly:
        that is the one place that (a) surfaces Ollama's actual 400 detail
        instead of a bare 500, and (b) retries once with more room when the
        model spent its whole budget thinking and never answered. Both used to
        exist only for chat_with_tools's callers — pulse judgments, memory
        extraction, directors and evals all call this method instead, and got
        neither: a thinking model handed them silent empty strings.
        """
        message = await self._post_chat(messages, None, temperature, max_tokens, images)
        if message is None:
            raise BrainUnavailable(f"{self.model} recusou a requisição de chat.")
        return message.get("content") or ""

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        images: list[str] | None = None,
    ) -> dict:
        """
        Tool-calling completion. Returns the full Ollama `message` dict, which may
        contain `tool_calls` when the model decides to act.

        A model without tool support does NOT "simply return normal content", as
        this docstring used to claim. Ollama rejects the request outright:

            400  {"error": "... llava:7b does not support tools"}

        which `raise_for_status` turned into an unhandled HTTPStatusError and a
        500 on /chat. With a vision-only model as the sole brain — capabilities
        ["completion", "vision"] — that made every chat request fail. So the fallback is real: drop the tools and ask again. The
        assistant answers without being able to act, which is the honest
        degradation, and the finding is remembered so the failed request is paid
        for once per process rather than on every message.

        `images` go to the same model in the same turn: the brain sees the photo
        and can call a tool about what it saw without anything handing the
        picture to a second model first.
        """
        use_tools = bool(tools) and self._supports_tools is not False
        message = await self._post_chat(messages, tools if use_tools else None,
                                        temperature, max_tokens, images)
        if message is not None:
            if use_tools:
                self._supports_tools = True
            return message

        # Only reachable when the model rejected the tools themselves.
        self._supports_tools = False
        logger.warning(
            "%s não suporta tool-calling; respondendo sem ferramentas. "
            "Para que o Jarvis possa agir, use um modelo com 'tools' "
            "(ex.: qwen3-vl:2b) em BRAIN_MODEL.",
            self.model,
        )
        message = await self._post_chat(messages, None, temperature, max_tokens, images)
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
        images: list[str] | None = None,
        _thinking_retry: bool = False,
    ) -> dict | None:
        """One /api/chat call. `None` means "this model refuses tools"."""
        payload = await self._payload(
            messages, tools=tools, temperature=temperature,
            max_tokens=max_tokens, images=images,
        )
        try:
            r = await self._client.post("/api/chat", json=payload)
            if r.status_code == 400 and "does not support tools" in r.text:
                return None
            if r.status_code == 400:
                # Every OTHER 400 used to escape as a bare HTTPStatusError and
                # reach the owner as "500 Internal Server Error", with Ollama's
                # actual complaint — the one sentence that says which field is
                # wrong — discarded unread. Ollama is specific; there is no
                # reason to throw that away and make the owner guess.
                detail = r.text.strip()[:400]
                logger.error("Ollama recusou a requisição (400): %s", detail)
                raise BrainUnavailable(f"Ollama recusou a requisição: {detail}")
            if r.status_code == 500 and not _thinking_retry:
                # Ollama's own qwen3vl adapter throws a bare 500 ("tool call
                # parsing failed: unexpected end of JSON input") when num_predict
                # cuts the model off mid tool-call — it started emitting
                # `{"name": "remember", "arguments": {...` and never got to the
                # closing brace. This is the SAME root cause as the thinking
                # retry below (not enough budget to finish what it started), so
                # it gets the same one bounded retry with more room, instead of
                # surfacing Ollama's internal parser crash as our own 500.
                used = payload["options"]["num_predict"]
                # Cap raised 2000->3200 on live evidence: with the full tool
                # catalog attached, this model needed MORE than 2000 tokens to
                # finish thinking about even a trivial greeting (measured live,
                # 2026-08-07) — the old cap meant the retry itself always lost
                # too. Still finite: a request that needs more than this is
                # treated as genuinely stuck, not chased forever.
                retry_budget = min(max(used * 3, 900), 3200)
                logger.warning(
                    "%s: Ollama 500 (provável tool call truncado em num_predict=%d) "
                    "— retentando com num_predict=%d",
                    self.model, used, retry_budget,
                )
                return await self._post_chat(
                    messages, tools, temperature, retry_budget, images,
                    _thinking_retry=True,
                )
            r.raise_for_status()
            message = r.json().get("message", {"role": "assistant", "content": ""})
            if not (message.get("content") or "").strip() and message.get("thinking"):
                # qwen3-vl thinks even when told not to: `think: false` is sent
                # whenever the model reports the capability, and this one still
                # emits a <think> block that Ollama splits into its own field.
                # If num_predict runs out mid-thought, `content` is empty and the
                # owner gets a blank reply from a model that worked for minutes.
                logger.warning(
                    "%s gastou a resposta pensando e não chegou a responder "
                    "(num_predict=%s). O raciocínio começa com: %.120s",
                    self.model, payload["options"]["num_predict"], message["thinking"],
                )
                if not _thinking_retry:
                    # One bounded retry with real headroom, rather than handing
                    # the owner silence. A model that never stops thinking would
                    # otherwise cost this every single message forever — capping
                    # the retry itself (not just counting attempts) keeps a
                    # single bad turn from becoming an unbounded one.
                    used = payload["options"]["num_predict"]
                    # Cap raised 2000->3200 on live evidence: with the full tool
                    # catalog attached, this model needed MORE than 2000 tokens
                    # to finish thinking about even a trivial greeting (measured
                    # live, 2026-08-07) — the old cap meant the retry itself
                    # always lost too. Still finite: a request needing more
                    # than this is treated as genuinely stuck, not chased
                    # forever.
                    retry_budget = min(max(used * 3, 900), 3200)
                    logger.info(
                        "retentando %s com num_predict=%d para o raciocínio terminar",
                        self.model, retry_budget,
                    )
                    return await self._post_chat(
                        messages, tools, temperature, retry_budget, images,
                        _thinking_retry=True,
                    )
            return message
        except httpx.ConnectError as e:
            raise BrainUnavailable(
                f"Ollama não respondeu em {self.endpoint}. Rode `ollama serve`."
            ) from e
        except httpx.HTTPStatusError as e:
            # Reached only when the retry above ALSO failed (or status was
            # something other than 400/500): a bare HTTPStatusError used to
            # leak past here as an opaque 500 from OUR api, indistinguishable
            # from a bug in this kernel rather than Ollama's own response.
            raise BrainUnavailable(
                f"Ollama respondeu {e.response.status_code} em /api/chat "
                f"(mesmo após nova tentativa)."
            ) from e

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        images: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Token-by-token streaming completion."""
        payload = await self._payload(
            messages, stream=True, temperature=temperature,
            max_tokens=max_tokens, images=images,
        )
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
            body: dict = {"model": self.embedding_model, "prompt": text}
            if settings.embedding_num_batch:
                body["options"] = {"num_batch": settings.embedding_num_batch}
            r = await self._client.post("/api/embeddings", json=body, timeout=30.0)
            r.raise_for_status()
            return r.json().get("embedding", [])
        except httpx.ConnectError as e:
            raise BrainUnavailable(
                f"Ollama não respondeu em {self.endpoint}. "
                f"Rode `ollama pull {self.embedding_model}`."
            ) from e
