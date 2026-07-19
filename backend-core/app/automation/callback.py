"""
CallbackHandler — n8n → Kernel bidirectional bridge.

n8n workflows call POST /api/v1/automations/callback with an action name and
params. This handler routes to the appropriate kernel service and returns the
result as JSON that n8n can use in subsequent workflow nodes.

This is what turns n8n from a one-way trigger into a true bidirectional
platform where workflows can:
  - Query memory to make decisions
  - Store results back to the knowledge graph
  - Publish events that trigger other kernel subsystems
  - Read the current world model state
  - Dispatch actions to devices
  - Call any registered API capability
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.models import Owner

logger = logging.getLogger("sexta-feira.automation.callback")


class CallbackRequest(BaseModel):
    """Request body for the n8n callback endpoint."""
    action: str = Field(..., description="The action to execute")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")


class CallbackHandler:
    """Routes n8n callback actions to the appropriate kernel services."""

    def __init__(self, kernel) -> None:
        self.kernel = kernel

    async def handle(self, db: Session, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a callback action and return the result."""
        handler = self._get_handler(action)
        if handler is None:
            return {"ok": False, "error": f"Ação desconhecida: {action}"}
        try:
            return await handler(db, params)
        except Exception as e:
            logger.warning("callback '%s' failed: %s", action, e)
            return {"ok": False, "error": str(e)}

    def _get_handler(self, action: str):
        mapping = {
            "recall": self._recall,
            "remember": self._remember,
            "event": self._event,
            "world": self._world,
            "world_set": self._world_set,
            "schedule": self._schedule,
            "action": self._action,
            "capabilities": self._capabilities,
            "call_api": self._call_api,
            "learning": self._learning,
            "lessons": self._lessons,
            "goals": self._goals,
            "health": self._health,
        }
        return mapping.get(action)

    async def _owner_id(self, db: Session, params: dict) -> str | None:
        """Resolve owner_id from params or get the first owner."""
        owner_id = params.get("owner_id")
        if owner_id:
            return owner_id
        owner = db.query(Owner).first()
        return owner.id if owner else None

    # ── Action implementations ──

    async def _recall(self, db: Session, params: dict) -> dict:
        """Search the knowledge graph for relevant memories."""
        memory = self.kernel.memory
        if not memory:
            return {"ok": False, "error": "Memória indisponível"}
        query = params.get("query", "")
        if not query:
            return {"ok": False, "error": "Parâmetro 'query' é obrigatório"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        results = await memory.recall_graph(db, owner_id, query)
        return {
            "ok": True,
            "count": len(results),
            "results": [
                {
                    "id": m.id,
                    "title": m.title,
                    "content": m.content,
                    "kind": m.kind,
                    "importance": m.importance,
                    "source": m.source,
                }
                for m in results
            ],
        }

    async def _remember(self, db: Session, params: dict) -> dict:
        """Save a fact to the knowledge graph."""
        memory = self.kernel.memory
        if not memory:
            return {"ok": False, "error": "Memória indisponível"}
        content = params.get("content", "")
        if not content:
            return {"ok": False, "error": "Parâmetro 'content' é obrigatório"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        m = await memory.remember(
            db, owner_id, content,
            kind=params.get("kind", "fact"),
            importance=float(params.get("importance", 0.5)),
            source=params.get("source", "automation"),
            title=params.get("title"),
        )
        return {"ok": True, "id": m.id, "title": m.title, "content": m.content}

    async def _event(self, db: Session, params: dict) -> dict:
        """Publish an event to the event bus."""
        events = self.kernel.events
        if not events:
            return {"ok": False, "error": "EventBus indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        event_type = params.get("type", "")
        if not event_type:
            return {"ok": False, "error": "Parâmetro 'type' é obrigatório"}
        ev = await events.publish(
            db, owner_id, event_type,
            payload=params.get("payload"),
            source=params.get("source", "automation"),
            correlation_id=params.get("correlation_id"),
            idempotency_key=params.get("idempotency_key"),
        )
        return {"ok": True, "event_id": ev.id, "type": ev.type, "sequence": ev.sequence}

    async def _world(self, db: Session, params: dict) -> dict:
        """Read the current world model state."""
        world = self.kernel.world
        if not world:
            return {"ok": False, "error": "World Model indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        digest = world.context_digest(db, owner_id)
        return {"ok": True, "state": digest}

    async def _world_set(self, db: Session, params: dict) -> dict:
        """Set a fact in the world model."""
        world = self.kernel.world
        if not world:
            return {"ok": False, "error": "World Model indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        key = params.get("key", "")
        value = params.get("value", "")
        if not key:
            return {"ok": False, "error": "Parâmetros 'key' e 'value' são obrigatórios"}
        f = world.set_fact(
            db, owner_id, key, value,
            category=params.get("category", "context"),
            source=params.get("source", "automation"),
            is_inference=bool(params.get("is_inference", False)),
        )
        return {"ok": True, "key": f.key, "value": f.value, "category": f.category}

    async def _schedule(self, db: Session, params: dict) -> dict:
        """Schedule a reminder or action."""
        scheduler = self.kernel.scheduler
        if not scheduler:
            return {"ok": False, "error": "Scheduler indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        from datetime import datetime
        due_at_str = params.get("due_at", "")
        if not due_at_str:
            return {"ok": False, "error": "Parâmetro 'due_at' (ISO 8601) é obrigatório"}
        try:
            due_at = datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
        except ValueError:
            return {"ok": False, "error": f"'due_at' inválido: {due_at_str}. Use ISO 8601."}
        task = scheduler.schedule(
            db, owner_id,
            kind=params.get("kind", "reminder"),
            due_at=due_at,
            text=params.get("text"),
            device=params.get("device"),
            action=params.get("action"),
            params=params.get("params"),
            recurrence_seconds=params.get("recurrence_seconds"),
        )
        return {"ok": True, "task_id": task.id, "kind": task.kind, "due_at": task.due_at.isoformat()}

    async def _action(self, db: Session, params: dict) -> dict:
        """Dispatch an action to a device."""
        actions = self.kernel.actions
        if not actions:
            return {"ok": False, "error": "ActionService indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        selector = params.get("device", "")
        action = params.get("action", "")
        if not selector or not action:
            return {"ok": False, "error": "Parâmetros 'device' e 'action' são obrigatórios"}
        result = await actions.dispatch(
            db, owner_id, selector, action, params.get("params", {}),
        )
        return result

    async def _capabilities(self, db: Session, params: dict) -> dict:
        """List registered API capabilities."""
        connectors = self.kernel.connectors
        if not connectors:
            return {"ok": False, "error": "Conectores indisponíveis"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        caps = connectors.list_capabilities(db, owner_id, params.get("query"))
        return {"ok": True, "count": len(caps), "capabilities": caps}

    async def _call_api(self, db: Session, params: dict) -> dict:
        """Execute an API capability by name."""
        connectors = self.kernel.connectors
        if not connectors:
            return {"ok": False, "error": "Conectores indisponíveis"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        capability = params.get("capability", "")
        if not capability:
            return {"ok": False, "error": "Parâmetro 'capability' é obrigatório"}
        result = await connectors.invoke(db, owner_id, capability, params.get("params", {}))
        return result

    async def _learning(self, db: Session, params: dict) -> dict:
        """Record a learning observation."""
        learning = self.kernel.learning
        if not learning:
            return {"ok": False, "error": "LearningEngine indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        entry = await learning.record(
            db, owner_id, params.get("context", ""),
            observation=params.get("observation"),
            quality=float(params.get("quality", 0.5)),
            lesson=params.get("lesson"),
            tag=params.get("tag"),
            source=params.get("source", "automation"),
        )
        return {"ok": True, "id": entry.id, "quality": entry.quality, "lesson": entry.lesson}

    async def _lessons(self, db: Session, params: dict) -> dict:
        """List recent learnings."""
        learning = self.kernel.learning
        if not learning:
            return {"ok": False, "error": "LearningEngine indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        rows = learning.lessons(db, owner_id, tag=params.get("tag"), limit=params.get("limit", 30))
        return {
            "ok": True,
            "count": len(rows),
            "lessons": [
                {"id": r.id, "context": r.context, "lesson": r.lesson,
                 "quality": r.quality, "tag": r.tag, "created_at": r.created_at}
                for r in rows
            ],
        }

    async def _goals(self, db: Session, params: dict) -> dict:
        """List current goals from the planning engine."""
        planning = self.kernel.planning
        if not planning:
            return {"ok": False, "error": "PlanningEngine indisponível"}
        owner_id = await self._owner_id(db, params)
        if not owner_id:
            return {"ok": False, "error": "Nenhum dono configurado"}
        goals = planning.list_goals(db, owner_id, status=params.get("status"))
        return {
            "ok": True,
            "count": len(goals),
            "goals": [
                {
                    "id": g.id, "title": g.title, "description": g.description,
                    "status": g.status, "priority": g.priority,
                    "progress": g.progress, "due_at": g.due_at,
                }
                for g in goals
            ],
        }

    async def _health(self, db: Session, params: dict) -> dict:
        """Simple health check for n8n callbacks."""
        brain_ok = await self.kernel.brain.health() if self.kernel.brain else False
        return {
            "ok": True,
            "kernel": "running",
            "brain_online": brain_ok,
            "brain_model": self.kernel.brain.model if self.kernel.brain else None,
        }
