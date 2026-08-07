"""
Prompt compression.

On CPU the read phase dominates: every prompt token is paid before the first
reply token exists. A conversation that grows without bound therefore gets
slower every single turn, and the tool scratchpad is the worst of it — raw
`tool_calls` JSON and raw results, written to be read exactly once, carried
forever after.

The line these tests hold is that compression must never buy speed with
correctness. Dropping the system prompt or the question would make every answer
faster and some of them wrong, which is not a trade worth having.
"""
from __future__ import annotations

from app.brain.cognition import _compression_budget
from app.brain.compression import compress, estimate_tokens, strip_tool_scratchpad
from app.core.config import settings

SYSTEM = {"role": "system", "content": "Você é o Sexta-Feira."}


def turn(role: str, text: str) -> dict:
    return {"role": role, "content": text}


def tool_turn() -> list[dict]:
    return [
        {"role": "assistant", "content": "Vou anotar isso.",
         "tool_calls": [{"function": {"name": "remember_about_me",
                                      "arguments": {"key": "nome", "value": "Matheus"}}}]},
        {"role": "tool", "tool_name": "remember_about_me", "content": "Anotado: nome = Matheus"},
    ]


# ---------------------------------------------------------------- scratchpad


def test_spent_tool_payloads_are_dropped():
    msgs = [SYSTEM, turn("user", "meu nome é Matheus"), *tool_turn(), turn("user", "e agora?")]
    out = strip_tool_scratchpad(msgs, keep_last=0)

    assert not any(m.get("role") == "tool" for m in out), "resultado de ferramenta sobreviveu"
    assert not any(m.get("tool_calls") for m in out), "payload de tool_calls sobreviveu"


def test_the_assistant_still_says_what_it_did():
    """Deleting the whole message would leave a reply to nothing."""
    msgs = [turn("user", "anota"), *tool_turn()]
    out = strip_tool_scratchpad(msgs, keep_last=0)

    assistant = [m for m in out if m["role"] == "assistant"]
    assert assistant, "o turno do assistente sumiu junto com o payload"
    assert assistant[0]["content"] == "Vou anotar isso."


def test_a_tool_only_turn_leaves_no_empty_message():
    """An assistant turn that was ONLY a call has no text left to keep.

    Emitting it as an empty message is worse than dropping it: some models treat
    a blank turn as a malformed conversation.
    """
    msgs = [
        turn("user", "anota"),
        {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "x", "arguments": {}}}]},
        {"role": "tool", "content": "ok"},
    ]
    out = strip_tool_scratchpad(msgs, keep_last=0)
    assert all(str(m.get("content") or "").strip() for m in out)


def test_the_most_recent_rounds_are_preserved():
    """The current turn's tool payload is the one the model still needs."""
    msgs = [turn("user", "a"), *tool_turn()]
    out = strip_tool_scratchpad(msgs, keep_last=2)
    assert any(m.get("tool_calls") for m in out)
    assert any(m.get("role") == "tool" for m in out)


# ---------------------------------------------------------------- compress


def test_a_short_conversation_is_untouched():
    msgs = [SYSTEM, turn("user", "oi")]
    out, stats = compress(msgs, max_tokens=2048)
    assert out == msgs
    assert stats["dropped"] == 0


def test_a_long_conversation_shrinks():
    msgs = [SYSTEM] + [turn("user", "pergunta longa " * 60) for _ in range(30)]
    before = estimate_tokens(msgs)
    out, stats = compress(msgs, max_tokens=512, keep_recent=4)

    assert estimate_tokens(out) < before
    assert stats["dropped"] > 0
    assert stats["tokens_after"] < stats["tokens_before"]


def test_the_system_prompt_always_survives():
    """It carries the assistant's identity and the owner model. Losing it makes
    answers wrong, not slow."""
    msgs = [SYSTEM] + [turn("user", "x " * 200) for _ in range(40)]
    out, _ = compress(msgs, max_tokens=128, keep_recent=2)
    assert any(m is SYSTEM or m.get("content") == SYSTEM["content"] for m in out)


def test_the_latest_question_always_survives():
    """Compressing away what was just asked would be fast and useless."""
    latest = turn("user", "ESTA é a pergunta")
    msgs = [SYSTEM] + [turn("user", "ruído " * 100) for _ in range(40)] + [latest]
    out, _ = compress(msgs, max_tokens=128, keep_recent=3)
    assert out[-1]["content"] == latest["content"]


def test_dropped_history_is_summarised_not_silently_lost():
    msgs = [SYSTEM] + [turn("user", f"assunto {i} " * 60) for i in range(20)]
    out, stats = compress(msgs, max_tokens=256, keep_recent=3)

    assert stats["dropped"] > 0
    summaries = [m for m in out if m["role"] == "system" and "Resumo" in str(m.get("content"))]
    assert summaries, "turnos foram descartados sem deixar resumo"


def test_a_custom_summariser_is_used_when_given():
    called = {}

    def summarise(dropped):
        called["n"] = len(dropped)
        return "RESUMO PERSONALIZADO"

    msgs = [SYSTEM] + [turn("user", "x " * 120) for _ in range(30)]
    out, _ = compress(msgs, max_tokens=200, keep_recent=2, summariser=summarise)

    assert called.get("n", 0) > 0
    assert any("RESUMO PERSONALIZADO" in str(m.get("content")) for m in out)


# ---------------------------------------------------------- budget resolution
#
# cognition._compression_budget decides WHAT `compress()` above targets. These
# tests hold the gap Step 3 closed: on a fresh install BRAIN_NUM_CTX is 0
# ("let Ollama decide"), and compression used to be gated on that being
# truthy — so it was a no-op until the owner ran the optimizer once. It must
# now fall back to a real number instead of skipping compression.


def test_an_unmeasured_machine_still_gets_a_real_budget(monkeypatch):
    monkeypatch.setattr(settings, "brain_num_ctx", 0)
    monkeypatch.setattr(settings, "prompt_compression_max_tokens", 3072)
    monkeypatch.setattr(settings, "brain_num_ctx_vision", 8192)

    budget = _compression_budget([turn("user", "oi")])

    assert budget == 3072


def test_a_measured_ctx_wins_over_the_guess(monkeypatch):
    monkeypatch.setattr(settings, "brain_num_ctx", 6000)
    monkeypatch.setattr(settings, "prompt_compression_max_tokens", 3072)
    monkeypatch.setattr(settings, "brain_num_ctx_vision", 8192)

    budget = _compression_budget([turn("user", "oi")])

    assert budget == 6000


def test_an_image_turn_never_compresses_below_the_vision_floor(monkeypatch):
    """The picture must not be trimmed out from under its own num_ctx ceiling."""
    monkeypatch.setattr(settings, "brain_num_ctx", 0)
    monkeypatch.setattr(settings, "prompt_compression_max_tokens", 3072)
    monkeypatch.setattr(settings, "brain_num_ctx_vision", 8192)

    with_image = [{"role": "user", "content": "o que é isso?", "images": ["base64..."]}]
    budget = _compression_budget(with_image)

    assert budget == 8192


def test_an_image_turn_keeps_a_measured_ctx_above_the_vision_floor(monkeypatch):
    """A real measurement above the floor is information; the floor must not lower it."""
    monkeypatch.setattr(settings, "brain_num_ctx", 12000)
    monkeypatch.setattr(settings, "prompt_compression_max_tokens", 3072)
    monkeypatch.setattr(settings, "brain_num_ctx_vision", 8192)

    with_image = [{"role": "user", "content": "o que é isso?", "images": ["base64..."]}]
    budget = _compression_budget(with_image)

    assert budget == 12000


def test_default_budget_actually_shrinks_a_long_conversation():
    """End-to-end: the resolved default budget is a real ceiling `compress()`
    enforces, not a number so large it never bites."""
    msgs = [SYSTEM] + [turn("user", "pergunta longa " * 60) for _ in range(60)]
    before = estimate_tokens(msgs)

    out, stats = compress(msgs, max_tokens=_compression_budget(msgs))

    assert estimate_tokens(out) < before
    assert stats["dropped"] > 0
    assert any(m is SYSTEM or m.get("content") == SYSTEM["content"] for m in out)
    assert out[-1]["content"] == msgs[-1]["content"]
