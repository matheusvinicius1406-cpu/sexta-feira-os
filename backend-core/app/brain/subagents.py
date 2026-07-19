"""
Sub-agents — the brain delegates focused sub-tasks to local helpers.

Sexta-Feira can spin up a transient specialist (researcher, planner, …) that runs
on the SAME local model, with a RESTRICTED toolset, does its bit, and returns a
concise result to the main brain. Everything is local and owner-scoped, so it
never breaks 'só meu'. Sub-agents get a read/knowledge toolset by default and
never receive `delegate`, so there's no runaway recursion and no irreversible
real-world action without the main brain deciding.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.brain.engine import LocalBrain
from app.core.config import settings

logger = logging.getLogger("sexta-feira.subagents")


class SubAgentRunner:
    def __init__(self, brain: LocalBrain, toolkit):
        self.brain = brain
        self.toolkit = toolkit  # shared ToolKit; we use a restricted subset here

    async def run(self, db: Session, owner_id: str, role: str, task: str) -> str:
        """Run a focused sub-agent and return its final answer text."""
        system = (
            f"Você é um sub-agente '{role}' auxiliando a Sexta-Feira. "
            "Foque SÓ na tarefa dada. Use suas ferramentas quando ajudar e "
            "devolva um resultado conciso e direto — sem enrolação."
        )
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]
        tools = await self.toolkit.specs_subset(settings.subagent_allowed_tools)

        for _ in range(settings.subagent_max_rounds):
            msg = await self.brain.chat_with_tools(messages, tools=tools)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return msg.get("content", "")
            messages.append({
                "role": "assistant", "content": msg.get("content", ""), "tool_calls": tool_calls,
            })
            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                # Hard stop: a sub-agent can never delegate again (no recursion).
                if name in ("delegate", "consult_director"):
                    messages.append({"role": "tool", "content": "Sub-agentes não podem delegar."})
                    continue
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:  # noqa: BLE001
                        args = {}
                result = await self.toolkit.dispatch(name, args, db, owner_id)
                messages.append({"role": "tool", "content": result})

        final = await self.brain.chat_with_tools(messages)
        return final.get("content", "")
