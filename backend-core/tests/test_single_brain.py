"""
One model thinks, acts and sees. These tests hold that shape in place.

The kernel used to run two generative models: qwen2.5:3b could call tools but
was blind, llava:7b could see but reports ["completion", "vision"] with no
"tools" and refused every tool-calling request. On a 12 GB box that split cost
twice — two residents evicting each other, and no turn that could look at an
image and then act on what it saw, because only one of the two had hands.

What is easy to get wrong when merging them is not the model name. It is the
settings that quietly still assume two:

  * VISION_MODEL, whose empty value now MEANS "the brain sees" and must never
    be read raw, or the kernel goes off guessing at a model the owner named.
  * VISION_KEEP_ALIVE, which if applied to the shared model would let a single
    photo schedule the assistant's own eviction seconds later — Ollama tracks
    keep_alive per model, last write wins.

Both are one-line mistakes that raise nothing and are only felt as "the
assistant got slow again".
"""
from __future__ import annotations

import httpx
import pytest

from app.brain.engine import LocalBrain, attach_images
from app.core.config import Settings
from app.kernel.pipeline.steps.core_steps import wanted_models

# ── who sees ────────────────────────────────────────────────

def test_an_empty_vision_model_means_the_brain_sees():
    s = Settings(brain_model="qwen3-vl:2b", vision_model="")
    assert s.vision_model_resolved == "qwen3-vl:2b"
    assert s.vision_shares_the_brain


def test_a_named_vision_model_still_wins():
    """The escape hatch has to keep working, or this is a lock-in, not a default."""
    s = Settings(brain_model="qwen3-vl:2b", vision_model="llava:13b")
    assert s.vision_model_resolved == "llava:13b"
    assert not s.vision_shares_the_brain


# ── how long it stays in RAM ────────────────────────────────

def test_the_shared_brain_is_held_for_the_brains_keep_alive():
    """The bug this prevents: looking at a photo unloads the assistant.

    VISION_KEEP_ALIVE is 30s by design — right for a 4.7 GB model wanted only
    when the camera is used. Sent for the model that is ALSO holding the
    conversation, it means the next message pays a cold load, which is the exact
    thrash that merging the models was meant to end.
    """
    s = Settings(brain_model="qwen3-vl:2b", vision_model="",
                 brain_keep_alive="10m", vision_keep_alive="30s")
    assert s.vision_keep_alive_resolved == "10m"


def test_a_separate_vision_model_is_still_evicted_early():
    s = Settings(brain_model="qwen3-vl:2b", vision_model="llava:7b",
                 brain_keep_alive="10m", vision_keep_alive="30s")
    assert s.vision_keep_alive_resolved == "30s"


# ── what the boot check asks for ────────────────────────────

def test_one_model_filling_two_roles_is_reported_once(monkeypatch):
    """Otherwise an absent brain prints two warnings and the same pull twice."""
    s = Settings(brain_model="qwen3-vl:2b", vision_model="", embedding_model="nomic-embed-text")
    monkeypatch.setattr("app.core.config.settings", s)

    wanted = wanted_models()

    assert list(wanted) == ["qwen3-vl:2b", "nomic-embed-text"]
    assert wanted["qwen3-vl:2b"] == ["conversa e ferramentas", "visão"]


def test_a_separate_vision_model_is_asked_for_separately(monkeypatch):
    s = Settings(brain_model="qwen3-vl:2b", vision_model="llava:7b",
                 embedding_model="nomic-embed-text")
    monkeypatch.setattr("app.core.config.settings", s)

    wanted = wanted_models()

    assert wanted["qwen3-vl:2b"] == ["conversa e ferramentas"]
    assert wanted["llava:7b"] == ["visão"]


# ── seeing inside the conversation ──────────────────────────

def test_images_ride_on_the_last_user_message():
    messages = [
        {"role": "system", "content": "persona"},
        {"role": "user", "content": "o que é isto?"},
    ]
    out = attach_images(messages, ["BASE64"])

    assert out[-1]["images"] == ["BASE64"]
    assert "images" not in out[0], "a imagem foi parar na mensagem de sistema"


def test_attaching_images_does_not_touch_the_caller_s_history():
    """The list handed in is usually the stored conversation.

    Mutating it pins the photo to a persisted turn, and every later message in
    that conversation re-uploads it — the reply gets slower for a reason nobody
    can see in the transcript.
    """
    messages = [{"role": "user", "content": "o que é isto?"}]
    attach_images(messages, ["BASE64"])

    assert "images" not in messages[0]


def test_no_images_leaves_the_messages_exactly_as_they_were():
    messages = [{"role": "user", "content": "oi"}]
    assert attach_images(messages, None) is messages


# ── the capability probe ────────────────────────────────────

def _brain(handler, model: str = "qwen3-vl:2b") -> LocalBrain:
    brain = LocalBrain(model=model)
    brain._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    return brain


def _show(caps: list[str] | None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/show":
            return httpx.Response(200, json={} if caps is None else {"capabilities": caps})
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "ok"}})
    return handler


@pytest.mark.asyncio
async def test_capabilities_come_from_api_show():
    brain = _brain(_show(["completion", "vision", "tools", "thinking"]))

    assert await brain.capabilities() == {"completion", "vision", "tools", "thinking"}
    assert await brain.can_see()


@pytest.mark.asyncio
async def test_a_blind_model_is_reported_as_blind():
    brain = _brain(_show(["completion", "tools"]))
    assert not await brain.can_see()


@pytest.mark.asyncio
async def test_the_probe_is_paid_for_once():
    shows = []

    def handler(request):
        if request.url.path == "/api/show":
            shows.append(request)
            return httpx.Response(200, json={"capabilities": ["completion", "tools", "vision"]})
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "ok"}})

    brain = _brain(handler)
    for _ in range(3):
        await brain.chat([{"role": "user", "content": "oi"}])

    assert len(shows) == 1, f"perguntou as capacidades {len(shows)}x por processo"


@pytest.mark.asyncio
async def test_a_failed_probe_is_not_remembered_as_an_answer():
    """A kernel that boots seconds before Ollama must not conclude it is blind.

    Caching the failure would make that verdict permanent for the life of the
    process: no thinking flag, no honest boot report, and nothing to indicate
    why — the assistant simply behaves like a lesser model until restarted.
    """
    state = {"up": False}

    def handler(request):
        if request.url.path == "/api/show":
            if not state["up"]:
                raise httpx.ConnectError("ollama ainda subindo")
            return httpx.Response(200, json={"capabilities": ["completion", "tools", "vision"]})
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "ok"}})

    brain = _brain(handler)
    assert await brain.capabilities() == set()

    state["up"] = True
    assert await brain.capabilities() == {"completion", "tools", "vision"}


@pytest.mark.asyncio
async def test_thinking_is_only_ever_sent_to_a_model_that_thinks():
    """Ollama answers 400 'does not support thinking' otherwise.

    Sent blindly, that turns a working chat model into a kernel where every
    message 500s — the same class of failure as sending tools to llava.
    """
    bodies = []

    def handler(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        bodies.append(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "ok"}})

    await _brain(handler).chat([{"role": "user", "content": "oi"}])
    assert b'"think"' not in bodies[0]


@pytest.mark.asyncio
async def test_a_text_attachment_is_read_as_text_not_as_a_fake_image():
    """The text path used to send b"aGVsbG8=" — base64 for "hello" — as an image.

    PIL cannot open that, so `_prepare_image` raised and EVERY .txt/.md/.csv
    upload came back "Cannot decode image". The fake pixel existed only because
    reading text and looking at pictures were different models; with one brain
    the text is simply asked as text.
    """
    from app.brain.attachments import AttachmentAnalyzer

    class _Brain:
        def __init__(self):
            self.prompts: list[str] = []

        async def chat(self, messages, **kw):
            self.prompts.append(messages[0]["content"])
            return "resumo do arquivo"

    class _Eyes:
        async def analyze_image(self, *a, **kw):
            raise AssertionError("um .txt não pode ir pelo caminho de imagem")

    brain = _Brain()
    out = await AttachmentAnalyzer(_Eyes(), brain=brain).analyze(
        b"primeira linha\nsegunda linha", "notas.txt", "text/plain",
    )

    assert out["type"] == "text"
    assert "primeira linha" in brain.prompts[0], "o conteúdo do arquivo não chegou ao cérebro"
    assert "resumo do arquivo" in out["analysis"]


@pytest.mark.asyncio
async def test_a_thinking_model_is_told_not_to_think():
    """On CPU, thinking spends the reply budget on reasoning nobody reads."""
    bodies = []

    def handler(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools", "thinking"]})
        bodies.append(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "ok"}})

    await _brain(handler).chat([{"role": "user", "content": "oi"}])
    assert b'"think":false' in bodies[0].replace(b" ", b"")
