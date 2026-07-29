"""
Cognition — the reasoning loop that turns a message into a grounded reply.

Pipeline for every turn:
  1. Load / create the conversation and its recent history (persisted).
  2. Recall relevant long-term memories (semantic search over YOUR data).
  3. Assemble the prompt: persona + recalled memory + history + new message.
  4. Ask the LocalBrain (Ollama) — non-streaming or streaming.
  5. Persist both turns.
  6. Optionally auto-learn a durable fact from the exchange.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.brain.engine import LocalBrain
from app.brain.memory import PersistentMemory
from app.core.config import settings
from app.models.models import Conversation, Message

logger = logging.getLogger("sexta-feira.cognition")


class Cognition:
    def __init__(self, brain: LocalBrain, memory: PersistentMemory, toolkit=None, world=None):
        self.brain = brain
        self.memory = memory
        self.toolkit = toolkit  # ToolKit | None — enables agentic actions
        self.world = world      # WorldModel | None — the present + the owner model

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

        # Direct vault recall — read recently modified .md notes from the vault
        # and inject them as context. This gives the brain access to notes the
        # user just wrote, even before they're imported into the graph.
        if settings.obsidian_vault_path and settings.obsidian_vault_recall_max_notes > 0:
            try:
                from app.obsidian.recall import (  # noqa: E402
                    format_vault_context,
                    read_recent_vault_notes,
                )
                notes = read_recent_vault_notes(
                    settings.obsidian_vault_path,
                    max_notes=settings.obsidian_vault_recall_max_notes,
                )
                vault_ctx = format_vault_context(notes)
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

    async def _auto_learn(self, db: Session, owner_id: str, user_text: str, reply: str) -> None:
        """Ask the brain to distil a durable fact worth remembering (best-effort).

        Also writes the fact as an Obsidian .md note if obsidian_vault_path
        is configured in settings (auto-export).
        """
        if not settings.memory_auto_learn:
            return
        try:
            probe = [
                {"role": "system", "content":
                    "Extraia UM fato duradouro sobre o usuário desta troca (preferência, "
                    "pessoa, rotina, meta, detalhe pessoal). Se não houver nada digno de "
                    "memória de longo prazo, responda exatamente 'NADA'. Seja conciso."},
                {"role": "user", "content": f"Usuário: {user_text}\nAssistente: {reply}"},
            ]
            fact = (await self.brain.chat(probe, temperature=0.1, max_tokens=80)).strip()
            if fact and fact.upper() != "NADA" and len(fact) > 8:
                await self.memory.remember(
                    db, owner_id, fact, kind="fact", importance=0.6, source="auto_learned"
                )
                # Auto-export: write the learned fact as an Obsidian .md note
                if settings.obsidian_vault_path:
                    try:
                        from app.obsidian.exporter import export_auto_learned_fact  # noqa: E402
                        export_auto_learned_fact(
                            vault_path=settings.obsidian_vault_path,
                            title=fact[:80],
                            content=fact,
                            kind="fact",
                        )
                    except Exception as export_err:  # noqa: BLE001
                        logger.debug("auto-export to vault skipped: %s", export_err)
        except Exception as e:  # noqa: BLE001 — never let learning break the reply
            logger.debug("auto-learn skipped: %s", e)

    # ---------- public API ----------

    async def respond(
        self, db: Session, owner_id: str, user_text: str,
        conversation_id: str | None = None, device_id: str | None = None,
    ) -> tuple[str, str]:
        """Return (reply_text, conversation_id). Runs the agentic tool loop."""
        conv = self._get_or_create_conversation(db, owner_id, conversation_id, device_id)
        messages = await self._build_messages(db, owner_id, conv, user_text)
        reply = await self._run_with_tools(db, owner_id, messages)
        self._persist_turn(db, conv, "owner", user_text)
        self._persist_turn(db, conv, "assistant", reply)
        await self._auto_learn(db, owner_id, user_text, reply)
        return reply, conv.id

    async def _run_with_tools(self, db: Session, owner_id: str, messages: list[dict]) -> str:
        """
        Ask the brain; if it decides to act (tool_calls), execute the tools, feed
        the results back, and continue — until it produces a final answer. When
        tools are disabled/unavailable, this is a single plain completion.
        """
        use_tools = bool(self.toolkit) and settings.tools_enabled
        tools = await self.toolkit.specs() if use_tools else None

        for _ in range(settings.tool_max_rounds if tools else 1):
            msg = await self.brain.chat_with_tools(messages, tools=tools)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return msg.get("content", "")

            messages.append({
                "role": "assistant",
                "content": msg.get("content", ""),
                "tool_calls": tool_calls,
            })
            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:  # noqa: BLE001
                        args = {}
                result = await self.toolkit.dispatch(name, args, db, owner_id)
                logger.info("tool %s -> %s", name, result[:80])
                messages.append({"role": "tool", "content": result})

        # Ran out of rounds still wanting tools: get a final plain answer.
        final = await self.brain.chat_with_tools(messages)
        return final.get("content", "")

    async def respond_stream(
        self, db: Session, owner_id: str, user_text: str,
        conversation_id: str | None = None, device_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Yield {'conversation_id'|'chunk'|'done'} events; persists at the end."""
        conv = self._get_or_create_conversation(db, owner_id, conversation_id, device_id)
        messages = await self._build_messages(db, owner_id, conv, user_text)
        yield {"conversation_id": conv.id}
        parts: list[str] = []
        async for chunk in self.brain.stream_chat(messages):
            parts.append(chunk)
            yield {"chunk": chunk}
        reply = "".join(parts)
        self._persist_turn(db, conv, "owner", user_text)
        self._persist_turn(db, conv, "assistant", reply)
        await self._auto_learn(db, owner_id, user_text, reply)
        yield {"done": True}
