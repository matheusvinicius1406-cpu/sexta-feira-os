"""
DirectorService — permanent specialist agents ("Diretores", Agent System).

Directors are the formal evolution of transient sub-agents: they PERSIST, and the
learning from each delegation STAYS WITH THE DIRECTOR — as specialized memory on
the same graph substrate (Memory rows with source='director:<name>'), injected
into the director's context on the next delegation. Expertise accumulates.

Authority rules (Constitution, Art. IV/V) are enforced in code:
  * subordinate to the Kernel — a director acts only when delegated to;
  * restricted toolset (its `allowed_tools`, default = sub-agent subset);
  * no recursion — `delegate` / `consult_director` are hard-stopped;
  * owner-scoped, local model only ("só meu").

Every delegation is auditable: publishes `diretor.delegado` / `diretor.concluido`.
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Director, Memory

logger = logging.getLogger("sexta-feira.directors")

_BLOCKED_TOOLS = {"delegate", "consult_director"}
_EXPERTISE_IN_CONTEXT = 12

# The canonical starting cabinet (AGENT_SYSTEM.md). The owner can add more.
DEFAULT_DIRECTORS: list[dict] = [
    {"name": "engenharia", "title": "Diretor de Engenharia",
     "domain": "software, arquitetura, código, testes, infraestrutura e dispositivos de desenvolvimento"},
    {"name": "pesquisa", "title": "Diretor de Pesquisa",
     "domain": "investigar temas, comparar alternativas, resumir conhecimento e trazer fatos"},
    {"name": "seguranca", "title": "Diretor de Segurança",
     "domain": "privacidade, credenciais, riscos, boas práticas e o princípio 'só meu'"},
    {"name": "memoria", "title": "Diretor de Memória",
     "domain": "curadoria do grafo de memória: organizar, conectar e resumir o que o dono sabe"},
    {"name": "automacao", "title": "Diretor de Automação",
     "domain": "automações e fluxos (Teia), rotinas recorrentes e integrações entre serviços"},
    {"name": "aprendizagem", "title": "Diretor de Aprendizagem",
     "domain": "estudo do dono: planos de aprendizado, revisão, dificuldades recorrentes"},
    {"name": "dispositivos", "title": "Diretor de Dispositivos",
     "domain": "os corpos do sistema: celular, computador, carro, wearables e suas ações"},
]


class DirectorService:
    def __init__(self, brain, toolkit, memory, events=None):
        self.brain = brain      # LocalBrain
        self.toolkit = toolkit  # shared ToolKit (restricted per delegation)
        self.memory = memory    # PersistentMemory — the shared substrate
        self.events = events    # EventBus | None

    # ---------- cabinet management ----------

    def ensure_defaults(self, db: Session, owner_id: str) -> int:
        """Seed the canonical directors that don't exist yet (idempotent)."""
        existing = {d.name for d in self.list(db, owner_id)}
        created = 0
        for spec in DEFAULT_DIRECTORS:
            if spec["name"] not in existing:
                self.create(db, owner_id, spec["name"], spec["title"], spec["domain"])
                created += 1
        return created

    def create(
        self, db: Session, owner_id: str, name: str, title: str, domain: str,
        allowed_tools: list[str] | None = None,
    ) -> Director:
        """Create or update a director (upsert by owner+name)."""
        slug = (name or "").strip().lower()
        if not slug:
            raise ValueError("director needs a name")
        d = self.get(db, owner_id, slug)
        if d:
            d.title = title
            d.domain = domain
            d.allowed_tools = json.dumps(allowed_tools) if allowed_tools else None
        else:
            d = Director(
                id=str(uuid.uuid4()), owner_id=owner_id, name=slug, title=title,
                domain=domain,
                allowed_tools=json.dumps(allowed_tools) if allowed_tools else None,
            )
            db.add(d)
        db.commit()
        db.refresh(d)
        return d

    def get(self, db: Session, owner_id: str, name: str) -> Director | None:
        return (
            db.query(Director)
            .filter(Director.owner_id == owner_id, Director.name == (name or "").strip().lower())
            .first()
        )

    def list(self, db: Session, owner_id: str) -> list[Director]:
        return (
            db.query(Director)
            .filter(Director.owner_id == owner_id)
            .order_by(Director.name)
            .all()
        )

    # ---------- specialized memory (expertise stays with the director) ----------

    async def teach(
        self, db: Session, owner_id: str, name: str, content: str, importance: float = 0.6
    ) -> None:
        """Add one piece of expertise to a director's specialized memory."""
        await self.memory.remember(
            db, owner_id, content, kind="fact", importance=importance,
            source=f"director:{name}",
        )

    def expertise(self, db: Session, owner_id: str, name: str, limit: int = 50) -> list[Memory]:
        return (
            db.query(Memory)
            .filter(Memory.owner_id == owner_id, Memory.source == f"director:{name}")
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .all()
        )

    # ---------- delegation (the Kernel hands work to a specialist) ----------

    async def delegate(self, db: Session, owner_id: str, name: str, task: str) -> str:
        director = self.get(db, owner_id, name)
        if not director or not director.enabled:
            return f"Diretor '{name}' não existe. Diretores: " + ", ".join(
                d.name for d in self.list(db, owner_id)
            )
        await self._emit(db, owner_id, "diretor.delegado", {"director": director.name})

        messages = [
            {"role": "system", "content": self._persona(db, owner_id, director)},
            {"role": "user", "content": task},
        ]
        allowed = (
            json.loads(director.allowed_tools) if director.allowed_tools
            else settings.subagent_allowed_tools
        )
        tools = await self.toolkit.specs_subset(allowed)
        result = await self._tool_loop(db, owner_id, messages, tools)

        await self._consolidate(db, owner_id, director, task, result)
        await self._emit(db, owner_id, "diretor.concluido", {"director": director.name})
        return result

    def _persona(self, db: Session, owner_id: str, director: Director) -> str:
        system = (
            f"Você é o {director.title} do dono, um especialista permanente em: "
            f"{director.domain}. Você é subordinado ao Kernel: foque SÓ na tarefa "
            "delegada, use suas ferramentas quando ajudarem e devolva um resultado "
            "conciso e direto."
        )
        expertise = self.expertise(db, owner_id, director.name, _EXPERTISE_IN_CONTEXT)
        if expertise:
            notes = "\n".join(f"- {m.content}" for m in expertise)
            system += "\n\nSua expertise acumulada (use quando for útil):\n" + notes
        return system

    async def _tool_loop(
        self, db: Session, owner_id: str, messages: list[dict], tools: list[dict]
    ) -> str:
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
                tool_name = fn.get("name", "")
                # Hard stop: a director can never delegate onward (no recursion).
                if tool_name in _BLOCKED_TOOLS:
                    messages.append({"role": "tool", "content": "Diretores não podem delegar."})
                    continue
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:  # noqa: BLE001
                        args = {}
                result = await self.toolkit.dispatch(tool_name, args, db, owner_id)
                messages.append({"role": "tool", "content": result})
        final = await self.brain.chat_with_tools(messages)
        return final.get("content", "")

    async def _consolidate(
        self, db: Session, owner_id: str, director: Director, task: str, result: str
    ) -> None:
        """'O aprendizado permanece no Diretor': distil the takeaway into its memory."""
        try:
            probe = [
                {"role": "system", "content":
                    f"Você é o {director.title}. Destile em UMA frase o aprendizado "
                    "durável desta tarefa para seu domínio (algo útil na próxima vez). "
                    "Se não houver nada digno, responda exatamente 'NADA'."},
                {"role": "user", "content": f"Tarefa: {task}\nResultado: {result}"},
            ]
            lesson = (await self.brain.chat(probe, temperature=0.1, max_tokens=80)).strip()
            if lesson and lesson.upper() != "NADA" and len(lesson) > 8:
                await self.teach(db, owner_id, director.name, lesson)
        except Exception as e:  # noqa: BLE001 — consolidation must never break the result
            logger.debug("director consolidation skipped: %s", e)

    async def _emit(self, db: Session, owner_id: str, etype: str, payload: dict) -> None:
        if not self.events:
            return
        await self.events.publish(db, owner_id, etype, payload, source="directors")
