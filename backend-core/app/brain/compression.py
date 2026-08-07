"""
Prompt compression — spend the read budget on what the answer needs.

On a CPU box the READ phase dominates. Every token in the prompt is paid for
before the first token of the reply exists, so a conversation that grows without
bound gets slower every turn, forever, while the extra tokens contribute
progressively less.

Three cuts, in order of how much they return:

  1. Tool scratchpad. A tool round leaves an assistant message full of raw
     `tool_calls` JSON and a tool message full of raw results. Those exist for
     the model to read ONCE, in the turn that made the call. Carried forward
     they are pure cost: nobody re-reads last Tuesday's function arguments.
  2. Sliding window. Keep the most recent turns verbatim.
  3. Summary of what fell out of the window, so dropping history does not mean
     forgetting it.

What this deliberately does not do is touch the system prompt or the current
question. Compressing those trades latency for wrong answers, which is not a
trade — a fast reply to a question the model can no longer see is worthless.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger("sexta-feira.compression")

# Roughly four characters per token for Portuguese. Only used to decide WHETHER
# to compress; the model reports the real count afterwards.
CHARS_PER_TOKEN = 4


def estimate_tokens(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        total += len(str(m.get("content") or "")) // CHARS_PER_TOKEN
        if m.get("tool_calls"):
            total += len(json.dumps(m["tool_calls"], ensure_ascii=False)) // CHARS_PER_TOKEN
    return total


def strip_tool_scratchpad(messages: list[dict], keep_last: int = 0) -> list[dict]:
    """Drop tool calls and their results from all but the last `keep_last` turns.

    The assistant message that carried the call is KEPT, with its text, so the
    conversation still reads as if the assistant did something — only the
    machine-readable payload goes. Deleting the message entirely would leave the
    reply to a question nobody asked.
    """
    if keep_last > 0:
        head, tail = messages[:-keep_last], messages[-keep_last:]
    else:
        head, tail = messages, []

    out: list[dict] = []
    for m in head:
        if m.get("role") == "tool":
            continue                               # a result nobody will re-read
        if m.get("tool_calls"):
            kept = {k: v for k, v in m.items() if k != "tool_calls"}
            # An assistant turn that was ONLY a tool call has no text left; it
            # would arrive as an empty message, which some models treat as a
            # malformed conversation.
            if not str(kept.get("content") or "").strip():
                continue
            out.append(kept)
            continue
        out.append(m)
    return out + tail


def compress(
    messages: list[dict],
    max_tokens: int,
    keep_recent: int = 6,
    summariser=None,
) -> tuple[list[dict], dict]:
    """Fit `messages` into `max_tokens`, returning the result and what was done.

    `summariser(dropped) -> str` is optional and synchronous-free: when absent,
    dropped turns are replaced by a plain listing rather than silently vanishing.
    An owner must never discover that the assistant forgot something because the
    prompt budget quietly ate it.
    """
    before = estimate_tokens(messages)
    stats = {"tokens_before": before, "tokens_after": before, "dropped": 0, "steps": []}
    if before <= max_tokens or not messages:
        return messages, stats

    # The system prompt and the last message are never candidates: one carries
    # the assistant's identity and the owner's model, the other is the question.
    system = [m for m in messages if m.get("role") == "system"]
    body = [m for m in messages if m.get("role") != "system"]

    working = system + strip_tool_scratchpad(body, keep_last=2)
    if estimate_tokens(working) < before:
        stats["steps"].append("scratchpad de ferramentas removido")
    if estimate_tokens(working) <= max_tokens:
        stats["tokens_after"] = estimate_tokens(working)
        return working, stats

    inner = [m for m in working if m.get("role") != "system"]
    if len(inner) > keep_recent:
        dropped, recent = inner[:-keep_recent], inner[-keep_recent:]
        note = (
            summariser(dropped) if summariser
            else "Resumo do trecho anterior: "
                 + "; ".join(
                     f"{m.get('role')}: {str(m.get('content') or '')[:80]}"
                     for m in dropped[-4:]
                 )
        )
        working = system + [{"role": "system", "content": note}] + recent
        stats["dropped"] = len(dropped)
        stats["steps"].append(f"janela deslizante: {len(dropped)} turnos resumidos")

    stats["tokens_after"] = estimate_tokens(working)
    logger.info(
        "contexto comprimido: %d -> %d tokens (%s)",
        stats["tokens_before"], stats["tokens_after"], "; ".join(stats["steps"]) or "sem mudança",
    )
    return working, stats
