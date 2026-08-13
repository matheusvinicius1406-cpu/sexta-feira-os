"""
Cognition — the reasoning loop that turns a message into a grounded reply.

Pipeline for every turn:
  1. Load / create the conversation and its recent history (persisted).
  2. Recall relevant long-term memories (semantic search over YOUR data).
  3. Assemble the prompt: persona + recalled memory + history + new message.
  4. Ask the LocalBrain (Ollama) — non-streaming or streaming.
  5. Persist both turns.
  6. Kick off auto-learn in the background — the reply does not wait for it.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.brain.compression import compress
from app.brain.engine import LocalBrain, attach_images
from app.brain.memory import PersistentMemory
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.models import Conversation, Message

logger = logging.getLogger("sexta-feira.cognition")

# `<tool_call>{...}</tool_call>`, with the closing tag often missing when the
# model stops at the token limit mid-emission.
_INLINE_TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)", re.DOTALL)


def _recover_inline_tool_calls(content: str) -> tuple[list[dict], str]:
    """Pull tool calls a model wrote as text out of its own answer.

    Ollama exposes tool calls in a structured `tool_calls` field, but a small
    model does not always cooperate: it can write the ChatML markup into
    `content` instead of the structured field. The structured field is then
    empty, the caller concludes "no tools wanted", and hands the raw
    `<tool_call>{"name": "remember_about_me", ...}` to the owner as the reply.

    Returns the recovered calls (in Ollama's own shape, so the caller cannot
    tell them apart) and the content with the markup removed — what is left is
    whatever the model actually meant to say.
    """
    if "<tool_call>" not in content:
        return [], content

    calls: list[dict] = []
    for raw in _INLINE_TOOL_CALL.findall(content):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue                      # truncated mid-JSON; not a usable call
        name = parsed.get("name")
        if not name:
            continue
        calls.append({"function": {"name": name, "arguments": parsed.get("arguments", {})}})

    if calls:
        logger.info("recuperadas %d chamada(s) de ferramenta escritas como texto", len(calls))
    cleaned = _INLINE_TOOL_CALL.sub("", content).replace("<tool_call>", "").strip()
    return calls, cleaned


def _compression_budget(messages: list[dict]) -> int:
    """What compress() should target for this round.

    Mirrors engine.py::_payload's own vision-ceiling resolution so the two
    never disagree about how much context an image turn gets: a measured
    BRAIN_NUM_CTX wins over the guess, an unmeasured machine falls back to
    prompt_compression_max_tokens rather than skipping compression entirely
    (the gap this closes — compression used to be a no-op until the owner ran
    the optimizer once), and an image turn never compresses below the vision
    floor, or the picture would be trimmed out from under its own ceiling.
    """
    budget = settings.brain_num_ctx or settings.prompt_compression_max_tokens
    if settings.brain_num_ctx_vision and any(m.get("images") for m in messages):
        budget = max(budget, settings.brain_num_ctx_vision)
    return budget


class Cognition:
    def __init__(self, brain: LocalBrain, memory: PersistentMemory, toolkit=None, world=None,
                 extractor=None):
        self.brain = brain
        self.memory = memory
        self.toolkit = toolkit      # ToolKit | None — enables agentic actions
        self.world = world          # WorldModel | None — the present + the owner model
        self.extractor = extractor  # MemoryExtractor | None — typed multi-fact auto-learn
        # Auto-learn runs detached from the reply (see _spawn/drain). Same
        # pattern as TeiaTriggerManager._spawn: a plain asyncio.create_task with
        # no reference held is eligible for GC mid-flight, so completed tasks
        # discard themselves and in-flight ones are only ever reached through
        # this set.
        self._tasks: set[asyncio.Task] = set()

    # ---------- conversation helpers ----------

    def _get_or_create_conversation(
        self, db: Session, owner_id: str, conversation_id: str | None, device_id: str | None
    ) -> Conversation:
        if conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id, Conversation.owner_id == owner_id
            ).first()
            if conv:
                return conv
        conv = Conversation(
            id=str(uuid.uuid4()), owner_id=owner_id, device_id=device_id, title=None,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    def _recent_history(self, conv: Conversation) -> list[dict]:
        msgs = conv.messages[-settings.brain_context_messages:]
        role_map = {"owner": "user", "assistant": "assistant"}
        return [{"role": role_map.get(m.role, "user"), "content": m.content} for m in msgs]

    async def _build_messages(
        self, db: Session, owner_id: str, conv: Conversation, user_text: str
    ) -> list[dict]:
        # Networked recall: seed by similarity, then follow the links between
        # memories so connected knowledge comes along (Obsidian-style).
        memories = await self.memory.recall_graph(db, owner_id, user_text)
        system = settings.brain_persona
        # The present + the owner model: no request ever starts from zero.
        if self.world is not None:
            digest = self.world.context_digest(db, owner_id)
            if digest:
                system += (
                    "\n\nEstado atual e o que você sabe do agora "
                    "(considere sempre; inferências são marcadas):\n" + digest
                )
        if memories:
            recalled = "\n".join(f"- {m.content}" for m in memories)
            system += (
                "\n\nO que você já sabe sobre seu dono e como as coisas se conectam "
                "(use quando for útil, sem repetir mecanicamente):\n" + recalled
            )

        # Direct vault recall — covers ONLY the watcher-lag window, not the
        # whole vault. recall_graph (above) already surfaces vault content
        # semantically: importer.py embeds every note it imports, so once the
        # watcher has seen a file, the graph is the right way to find it —
        # ranked by relevance, not by "happened to be edited recently". This
        # is for the narrower gap: a note saved seconds ago, before the NEXT
        # poll (obsidian_watch_interval, default 30s) has picked it up. A
        # 72-HOUR default age window used to mean every turn re-scanned and
        # re-read every recently-touched file in the entire vault — on the
        # event loop, synchronously — to inject content the graph would
        # already have surfaced, days after any real freshness gap had closed.
        # 2x the interval covers a poll that landed a little late; content
        # older than that belongs to the graph, not this.
        if settings.obsidian_vault_path and settings.obsidian_vault_recall_max_notes > 0:
            try:
                from app.obsidian.recall import (  # noqa: E402
                    format_vault_context,
                    read_recent_vault_notes,
                )
                lag_hours = (2 * settings.obsidian_watch_interval) / 3600
                notes = await asyncio.to_thread(
                    read_recent_vault_notes,
                    settings.obsidian_vault_path,
                    max_notes=settings.obsidian_vault_recall_max_notes,
                    max_age_hours=lag_hours,
                )
                vault_ctx = format_vault_context(notes, max_chars=1200)
                if vault_ctx:
                    system += vault_ctx
            except Exception as e:  # noqa: BLE001
                logger.debug("vault recall skipped: %s", e)

        messages = [{"role": "system", "content": system}]
        messages.extend(self._recent_history(conv))
        messages.append({"role": "user", "content": user_text})
        return messages

    def _persist_turn(self, db: Session, conv: Conversation, role: str, content: str) -> None:
        db.add(Message(id=str(uuid.uuid4()), conversation_id=conv.id, role=role, content=content))
        conv.updated_at = datetime.now(UTC)
        if role == "owner" and not conv.title:
            conv.title = content[:60]
        db.commit()

    async def _auto_learn(self, owner_id: str, user_text: str, reply: str) -> None:
        """Distil durable memories from the exchange (best-effort, never breaks the reply).

        Runs detached (see _spawn) on its OWN session, never the request's: by
        the time a background task gets scheduled, the caller may already have
        returned and closed the request-scoped `db` FastAPI handed it, so
        reusing that session here would mean writing through a closed
        connection. `SessionLocal()` is cheap and this is the only place that
        needs one for the whole lifetime of the extraction.

        There is exactly one path: the MemoryExtractor. A second, single-fact
        fallback used to sit below `if self.extractor: ... return` — and the
        kernel always injects an extractor, so it never ran. Worse, the Obsidian
        auto-export lived only inside that fallback, which is why a learned fact
        never reached the vault. The export now hangs off the extractor's
        `on_stored` hook (wired in CognitionStep), on the path actually taken.
        """
        if not settings.memory_auto_learn or not self.extractor:
            return
        db = SessionLocal()
        try:
            # Typed multi-fact extraction, routed to graph memory + User Model,
            # and mirrored to the vault by the extractor's on_stored callback.
            await self.extractor.extract(db, owner_id, user_text, reply)
        except Exception as e:  # noqa: BLE001 — never let learning break the reply
            logger.debug("auto-learn skipped: %s", e)
        finally:
            db.close()

    def _spawn(self, coro) -> None:
        """Run a coroutine detached from the caller, keeping a reference so it
        isn't garbage-collected mid-flight. Mirrors TeiaTriggerManager._spawn."""
        try:
            task = asyncio.get_running_loop().create_task(coro)
        except RuntimeError:                # no loop — nothing to detach into
            coro.close()
            logger.debug("auto-learn não disparado: sem event loop")
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        """Await auto-learn tasks still in flight (used on shutdown/tests)."""
        while self._tasks:
            pending = list(self._tasks)
            await asyncio.gather(*pending, return_exceptions=True)

    # ---------- public API ----------

    async def respond(
        self, db: Session, owner_id: str, user_text: str,
        conversation_id: str | None = None, device_id: str | None = None,
        images: list[str] | None = None,
    ) -> tuple[str, str]:
        """Return (reply_text, conversation_id). Runs the agentic tool loop.

        `images` are base64 JPEGs (see vision.prepare_image) shown to the brain
        along with the message. They are NOT persisted with the turn: the text
        the brain wrote about the picture is what the conversation keeps, and
        storing the blob would re-send it on every later request forever.
        """
        conv = self._get_or_create_conversation(db, owner_id, conversation_id, device_id)
        messages = await self._build_messages(db, owner_id, conv, user_text)
        reply = await self._run_with_tools(db, owner_id, messages, images)
        self._persist_turn(db, conv, "owner", user_text)
        self._persist_turn(db, conv, "assistant", reply)
        self._spawn(self._auto_learn(owner_id, user_text, reply))
        return reply, conv.id

    async def _run_with_tools(
        self, db: Session, owner_id: str, messages: list[dict],
        images: list[str] | None = None,
    ) -> str:
        """
        Ask the brain; if it decides to act (tool_calls), execute the tools, feed
        the results back, and continue — until it produces a final answer. When
        tools are disabled/unavailable, this is a single plain completion.

        Seeing and acting are the same loop now, which is the whole reason for
        one model: the brain can look at the photo, decide it needs a tool, and
        answer using both. With vision in a separate model this was impossible —
        the picture was described by something that had no hands, and the reply
        was written by something that had never seen it.
        """
        use_tools = bool(self.toolkit) and settings.tools_enabled
        tools = await self.toolkit.specs() if use_tools else None

        # Attached ONCE, into the list every round reuses — not per round. The
        # image then sits in a stable prefix, so llama.cpp's KV cache carries it
        # across tool rounds; re-attaching each round would re-read the whole
        # picture every time, and on CPU that costs more than the tool call it
        # was supposed to inform.
        messages = attach_images(messages, images)

        # Every (tool, arguments) pair already executed in this turn. A small
        # model that does not notice its call was answered will ask for the very
        # same thing again, and each retry costs a full inference round: on CPU
        # that turned a one-round reply into four, ~30 s each. It also re-ran the
        # side effect — the same fact was written to the User Model four times.
        done: dict[str, str] = {}

        for _ in range(settings.tool_max_rounds if tools else 1):
            # Compress before each round, not just at the start: a tool round
            # ADDS the call payload and its result to the history, so the second
            # round reads a bigger prompt than the first. That growth is exactly
            # what makes a multi-round turn feel worse than a single one.
            if settings.prompt_compression:
                messages, _ = compress(messages, max_tokens=_compression_budget(messages))
            msg = await self.brain.chat_with_tools(messages, tools=tools)
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content", "")
            if not tool_calls and tools:
                # Small models sometimes emit the call as TEXT instead of using
                # the structured field — a literal
                # `<tool_call>{"name": ...}</tool_call>` lands in `content`.
                # Returned as-is, that markup would land on screen as the
                # assistant's answer: a reply became `<tool_call>\n{"name":
                # "remember_about_me"...`.
                tool_calls, content = _recover_inline_tool_calls(content)
            if not tool_calls:
                return content

            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            })
            repeats = 0
            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:  # noqa: BLE001
                        args = {}

                key = f"{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)}"
                if key in done:
                    repeats += 1
                    result = done[key]
                    logger.info("tool %s repetida — reaproveitando o resultado", name)
                else:
                    result = await self.toolkit.dispatch(name, args, db, owner_id)
                    done[key] = result
                    logger.info("tool %s -> %s", name, result[:80])

                # `tool_name` tells the model WHICH call this answers. Without it
                # a reply is an anonymous blob of text, which is precisely why it
                # kept asking again.
                messages.append({"role": "tool", "tool_name": name, "content": result})

            # Asking only for things it has already been given means it is stuck,
            # not working. Spending the remaining rounds on it buys nothing but
            # latency, so go straight to the final answer.
            if repeats == len(tool_calls):
                break

        # Ran out of rounds still wanting tools: get a final plain answer.
        final = await self.brain.chat_with_tools(messages)
        return final.get("content", "")

    async def respond_stream(
        self, db: Session, owner_id: str, user_text: str,
        conversation_id: str | None = None, device_id: str | None = None,
        images: list[str] | None = None,
    ) -> AsyncIterator[dict]:
        """Yield {'conversation_id'|'chunk'|'done'} events; persists at the end.

        Streaming has no tool loop — it is one completion, token by token — so
        the brain can see here but not act on what it sees. Use `respond` when
        the answer may need a tool.
        """
        conv = self._get_or_create_conversation(db, owner_id, conversation_id, device_id)
        messages = await self._build_messages(db, owner_id, conv, user_text)
        yield {"conversation_id": conv.id}
        parts: list[str] = []
        async for chunk in self.brain.stream_chat(messages, images=images):
            parts.append(chunk)
            yield {"chunk": chunk}
        reply = "".join(parts)
        self._persist_turn(db, conv, "owner", user_text)
        self._persist_turn(db, conv, "assistant", reply)
        self._spawn(self._auto_learn(owner_id, user_text, reply))
        yield {"done": True}
