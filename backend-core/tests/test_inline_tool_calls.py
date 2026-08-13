"""
Tool calls a small model writes as text instead of using the structured field.

Ollama returns tool calls in `message.tool_calls`. A small model does not always
cooperate: it can write the ChatML markup straight into `content` instead of the
structured field. The structured
field is then empty, the loop concludes no tool was wanted, and hands the markup
to the owner as the answer. Observed verbatim on screen:

    <tool_call>
    {"name": "remember_about_me", "arguments": {"category":"preferences", ...

Nothing failed. The request was 200, the "reply" was JSON, and the tool never
ran — so the fact the owner asked to be remembered was silently dropped.
"""
from __future__ import annotations

from app.brain.cognition import _recover_inline_tool_calls


def test_plain_answer_is_left_alone():
    calls, content = _recover_inline_tool_calls("Olá! Como posso ajudar?")
    assert calls == []
    assert content == "Olá! Como posso ajudar?"


def test_a_call_written_as_text_is_recovered():
    raw = (
        'Claro.\n<tool_call>\n{"name": "remember_about_me", '
        '"arguments": {"key": "nome", "value": "Matheus"}}\n</tool_call>'
    )
    calls, content = _recover_inline_tool_calls(raw)

    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "remember_about_me"
    assert calls[0]["function"]["arguments"] == {"key": "nome", "value": "Matheus"}
    assert "<tool_call>" not in content, "a marcação ficou na resposta do usuário"
    assert content == "Claro."


def test_the_recovered_shape_matches_ollama():
    """The caller must not be able to tell a recovered call from a native one."""
    calls, _ = _recover_inline_tool_calls('<tool_call>{"name": "x", "arguments": {}}</tool_call>')
    fn = calls[0]["function"]
    assert set(calls[0]) == {"function"}
    assert set(fn) == {"name", "arguments"}


def test_several_calls_are_all_recovered():
    raw = (
        '<tool_call>{"name": "a", "arguments": {}}</tool_call>'
        '<tool_call>{"name": "b", "arguments": {"q": 1}}</tool_call>'
    )
    calls, content = _recover_inline_tool_calls(raw)
    assert [c["function"]["name"] for c in calls] == ["a", "b"]
    assert content == ""


def test_a_truncated_call_is_not_half_executed():
    """Hitting the token limit mid-JSON must not produce a call from fragments.

    Acting on half an argument list is worse than not acting: the tool would run
    with silently missing fields.
    """
    calls, content = _recover_inline_tool_calls('<tool_call>\n{"name": "remember", "argum')
    assert calls == []
    assert "<tool_call>" not in content


def test_a_call_without_a_name_is_ignored():
    calls, _ = _recover_inline_tool_calls('<tool_call>{"arguments": {"q": 1}}</tool_call>')
    assert calls == []


def test_missing_closing_tag_still_recovers():
    """Models truncate the closing tag more often than the JSON."""
    calls, _ = _recover_inline_tool_calls('<tool_call>{"name": "a", "arguments": {}}')
    assert [c["function"]["name"] for c in calls] == ["a"]
