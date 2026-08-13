"""
A brain that cannot use tools must still answer.

`chat_with_tools` used to document that "models that don't support tools simply
return normal content — the caller handles both". Ollama does no such thing: it
rejects the request with

    400  {"error": "registry.ollama.ai/library/llava:7b does not support tools"}

`raise_for_status()` turned that into an unhandled exception and a 500 on
/api/v1/chat. Since llava:7b — a vision model, capabilities ["completion",
"vision"] — is this kernel's sole brain, EVERY chat request failed. The comment
asserting graceful degradation is what kept anyone from checking.

These tests use a stand-in Ollama that refuses tools exactly as the real one
does, so the fallback is proven against the actual failure, not a guess at it.

The brain now also asks /api/show what the model can do before its first
request. That probe is a different endpoint, and the stand-in below answers it
as an Ollama too old to report capabilities would — the empty answer that means
"unknown". This keeps these tests about the 400 fallback, which is the backstop
that must still work when the probe tells us nothing.
"""
from __future__ import annotations

import httpx
import pytest

from app.brain.engine import BrainUnavailable, LocalBrain

TOOLS = [{"type": "function", "function": {"name": "lembrar", "description": "d", "parameters": {}}}]


def _brain(handler) -> LocalBrain:
    brain = LocalBrain()
    brain._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    return brain


def _chat_calls(requests: list[httpx.Request]) -> list[bool]:
    """Did each /api/chat request carry tools? Capability probes are not chats."""
    return [b'"tools"' in r.content for r in requests if r.url.path == "/api/chat"]


def _refuses_tools(request: httpx.Request) -> httpx.Response:
    """What Ollama really does with a tool-less model."""
    if request.url.path == "/api/show":
        return httpx.Response(200, json={})          # no capabilities reported
    if b'"tools"' in request.content:
        return httpx.Response(
            400, json={"error": "registry.ollama.ai/library/llava:7b does not support tools"}
        )
    return httpx.Response(200, json={"message": {"role": "assistant", "content": "Ok."}})


@pytest.mark.asyncio
async def test_answers_even_when_the_model_refuses_tools():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return _refuses_tools(request)

    brain = _brain(handler)
    msg = await brain.chat_with_tools([{"role": "user", "content": "oi"}], tools=TOOLS)

    assert msg["content"] == "Ok.", "a resposta sem ferramentas não chegou ao chamador"
    assert _chat_calls(seen) == [True, False], (
        f"esperava uma tentativa com ferramentas e o reenvio sem elas; houve {_chat_calls(seen)}"
    )


@pytest.mark.asyncio
async def test_the_rejection_is_paid_for_only_once():
    """Retrying tools on every message would double every chat's latency."""
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return _refuses_tools(request)

    brain = _brain(handler)
    for _ in range(3):
        await brain.chat_with_tools([{"role": "user", "content": "oi"}], tools=TOOLS)

    tried = _chat_calls(seen).count(True)
    assert tried == 1, f"tentou usar ferramentas {tried}x; a recusa deveria ser lembrada"
    assert brain._supports_tools is False


@pytest.mark.asyncio
async def test_a_model_with_tools_keeps_them():
    """The fallback must not cost tool support where it exists."""
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        if request.url.path == "/api/show":
            return httpx.Response(200, json={})
        return httpx.Response(200, json={
            "message": {"role": "assistant", "content": "",
                        "tool_calls": [{"function": {"name": "lembrar", "arguments": {}}}]},
        })

    brain = _brain(handler)
    msg = await brain.chat_with_tools([{"role": "user", "content": "oi"}], tools=TOOLS)

    assert msg["tool_calls"], "as tool_calls do modelo foram perdidas"
    assert _chat_calls(seen) == [True]
    assert brain._supports_tools is True


@pytest.mark.asyncio
async def test_a_refusal_without_tools_is_not_blamed_on_tools():
    """If the model refuses the plain request too, say so instead of looping."""

    def handler(request):
        return httpx.Response(400, json={"error": "model does not support tools"})

    with pytest.raises(BrainUnavailable):
        await _brain(handler).chat_with_tools([{"role": "user", "content": "oi"}], tools=TOOLS)


@pytest.mark.asyncio
async def test_a_dead_ollama_is_still_reported_as_unavailable():
    """The new branch must not swallow the connection error it sits next to."""

    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(BrainUnavailable):
        await _brain(handler).chat_with_tools([{"role": "user", "content": "oi"}], tools=TOOLS)
