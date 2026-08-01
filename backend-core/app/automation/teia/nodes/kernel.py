"""
Kernel nodes — an automation reaching into the second brain itself.

This is what makes the Teia different from a generic workflow runner: memory, the
World Model, the event bus, the scheduler, goals, journal, habits, devices and
the owner's curated API capabilities are all first-class steps. All of it stays
on this machine and scoped to the one owner.

Every node here opens its own short-lived DB session (`context.session()`), so
workers running in parallel never share a Session.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata


def _due_from(quando: str | None, em_segundos: float | None) -> datetime:
    """Absolute ISO instant, or a relative offset from now."""
    if quando:
        parsed = datetime.fromisoformat(quando.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    if em_segundos is not None:
        return datetime.now(UTC) + timedelta(seconds=em_segundos)
    raise ValueError("informe 'quando' (ISO) ou 'em_segundos'")


# ---------------------------------------------------------------- memory


class _RememberConfig(BaseModel):
    conteudo: str = Field(..., min_length=1)
    titulo: str | None = None
    tipo: Literal["fact", "preference", "person", "routine", "note", "concept"] = "fact"
    importancia: float = Field(default=0.5, ge=0.0, le=1.0)


class RememberNode(Node):
    """Save a durable fact into the graph memory."""

    metadata = NodeMetadata(
        type="memoria_gravar", name="Gravar na memória", category="kernel",
        description="Guarda um fato duradouro no segundo cérebro.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _RememberConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        memory = context.services.require("memory")
        cfg = self.config
        with context.session() as db:
            saved = await memory.remember(
                db, context.owner_id, cfg.conteudo, kind=cfg.tipo,
                importance=cfg.importancia, source="teia", title=cfg.titulo,
            )
            return NodeOutput.single(
                {"id": saved.id, "conteudo": saved.content, "titulo": saved.title}
            )


class _RecallConfig(BaseModel):
    consulta: str = Field(..., min_length=1)
    quantidade: int = Field(default=6, ge=1, le=50)
    expandir_grafo: bool = True


class RecallNode(Node):
    """Search memory; emits one item per hit."""

    metadata = NodeMetadata(
        type="memoria_buscar", name="Buscar na memória", category="kernel",
        description="Procura na memória do dono e emite os resultados.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _RecallConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        memory = context.services.require("memory")
        cfg = self.config
        with context.session() as db:
            search = memory.recall_graph if cfg.expandir_grafo else memory.recall
            hits = await search(db, context.owner_id, cfg.consulta, cfg.quantidade)
            items = [
                {"id": m.id, "titulo": m.title, "conteudo": m.content,
                 "tipo": m.kind, "importancia": m.importance}
                for m in hits
            ]
        context.log(f"memória: {len(items)} resultado(s) para '{cfg.consulta}'")
        return NodeOutput(items={"main": items})


# ---------------------------------------------------------------- world / owner


class _WorldSetConfig(BaseModel):
    chave: str = Field(..., min_length=1)
    valor: Any = ""
    categoria: str = "other"
    inferencia: bool = False
    confianca: float = Field(default=1.0, ge=0.0, le=1.0)


class WorldSetNode(Node):
    """Update one truth about the present in the World Model."""

    metadata = NodeMetadata(
        type="mundo_definir", name="Definir estado do mundo", category="kernel",
        description="Atualiza um fato do presente (World Model).",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _WorldSetConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        world = context.services.require("world")
        cfg = self.config
        with context.session() as db:
            fact = world.set_fact(
                db, context.owner_id, cfg.chave, str(cfg.valor),
                category=cfg.categoria, source="teia",
                confidence=cfg.confianca, is_inference=cfg.inferencia,
            )
            return NodeOutput.single({"chave": fact.key, "valor": fact.value})


class _WorldGetConfig(BaseModel):
    chave: str = ""
    tudo: bool = False
    limite: int = Field(default=50, ge=1, le=500)


class WorldGetNode(Node):
    """Read the World Model — one key, or the whole snapshot."""

    metadata = NodeMetadata(
        type="mundo_ler", name="Ler estado do mundo", category="kernel",
        description="Lê um fato do presente, ou o retrato inteiro.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _WorldGetConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        world = context.services.require("world")
        cfg = self.config
        with context.session() as db:
            if cfg.tudo or not cfg.chave:
                rows = world.snapshot(db, context.owner_id, limit=cfg.limite)
                items = [
                    {"chave": f.key, "valor": f.value, "categoria": f.category,
                     "inferencia": f.is_inference}
                    for f in rows
                ]
                return NodeOutput(items={"main": items})
            fact = world.get_fact(db, context.owner_id, cfg.chave)
            if not fact:
                return NodeOutput(items={"main": []})
            return NodeOutput.single(
                {"chave": fact.key, "valor": fact.value, "categoria": fact.category}
            )


class _AttributeConfig(BaseModel):
    chave: str = Field(..., min_length=1)
    valor: Any = ""
    categoria: str = "other"


class OwnerAttributeNode(Node):
    """Record a durable trait of the owner (the User Model)."""

    metadata = NodeMetadata(
        type="dono_anotar", name="Anotar sobre o dono", category="kernel",
        description="Grava um traço duradouro do dono (User Model).",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _AttributeConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        world = context.services.require("world")
        cfg = self.config
        with context.session() as db:
            attribute = world.set_attribute(
                db, context.owner_id, cfg.chave, str(cfg.valor),
                category=cfg.categoria, source="teia",
            )
            return NodeOutput.single({"chave": attribute.key, "valor": attribute.value})


# ---------------------------------------------------------------- events


class _EventConfig(BaseModel):
    tipo: str = Field(..., min_length=1)
    dados: dict = Field(default_factory=dict)
    chave_idempotencia: str | None = None


class PublishEventNode(Node):
    """Publish an event on the kernel bus — other automations can react to it."""

    metadata = NodeMetadata(
        type="evento_publicar", name="Publicar evento", category="kernel",
        description="Emite um evento no barramento do kernel.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _EventConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        events = context.services.require("events")
        cfg = self.config
        with context.session() as db:
            event = await events.publish(
                db, context.owner_id, cfg.tipo, cfg.dados,
                source=f"teia:{context.workflow_slug}",
                correlation_id=context.execution_id,
                idempotency_key=cfg.chave_idempotencia,
            )
            return NodeOutput.single({"id": event.id, "tipo": event.type})


# ---------------------------------------------------------------- schedule


class _ScheduleConfig(BaseModel):
    tipo: Literal["reminder", "action", "briefing"] = "reminder"
    texto: str = ""
    quando: str | None = None                 # ISO instant
    em_segundos: float | None = Field(default=None, ge=0)
    dispositivo: str | None = None
    acao: str | None = None
    parametros: dict = Field(default_factory=dict)
    repetir_a_cada_segundos: int | None = Field(default=None, ge=30)


class ScheduleNode(Node):
    """Put a future intention on the kernel's scheduler."""

    metadata = NodeMetadata(
        type="agendar", name="Agendar", category="kernel",
        description="Cria um lembrete ou uma ação futura.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _ScheduleConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        scheduler = context.services.require("scheduler")
        cfg = self.config
        due = _due_from(cfg.quando, cfg.em_segundos)
        with context.session() as db:
            task = scheduler.schedule(
                db, context.owner_id, kind=cfg.tipo, due_at=due, text=cfg.texto,
                device=cfg.dispositivo, action=cfg.acao, params=cfg.parametros,
                recurrence_seconds=cfg.repetir_a_cada_segundos,
            )
            return NodeOutput.single(
                {"id": task.id, "tipo": task.kind, "quando": due.isoformat(timespec="minutes")}
            )


# ---------------------------------------------------------------- devices


class _NotifyConfig(BaseModel):
    texto: str = Field(..., min_length=1)
    dispositivo: str = "celular"


class NotifyNode(Node):
    """Tell the owner something, on one of their devices.

    A device that is offline still gets the command: it is queued and delivered on
    reconnect, so `entregue: false` means "waiting", not "lost".
    """

    metadata = NodeMetadata(
        type="notificar", name="Notificar o dono", category="kernel",
        description="Envia um aviso para um dispositivo do dono.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _NotifyConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        actions = context.services.require("actions")
        cfg = self.config
        with context.session() as db:
            out = await actions.dispatch(
                db, context.owner_id, cfg.dispositivo, "notify", {"text": cfg.texto}
            )
        if not out.get("ok"):
            raise RuntimeError(out.get("error", "não consegui notificar"))
        return NodeOutput.single({
            "ok": True, "dispositivo": out.get("device"),
            "entregue": out.get("delivered", False), "texto": cfg.texto,
        })


class _DeviceActionConfig(BaseModel):
    dispositivo: str = "celular"
    acao: str = Field(..., min_length=1)
    parametros: dict = Field(default_factory=dict)


class DeviceActionNode(Node):
    """Make a device do something native (open an app, navigate, call...)."""

    metadata = NodeMetadata(
        type="dispositivo_acao", name="Ação no dispositivo", category="kernel",
        description="Manda um corpo do dono executar uma ação nativa.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _DeviceActionConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        actions = context.services.require("actions")
        cfg = self.config
        with context.session() as db:
            out = await actions.dispatch(
                db, context.owner_id, cfg.dispositivo, cfg.acao, cfg.parametros
            )
        if not out.get("ok"):
            raise RuntimeError(out.get("error", "não consegui despachar a ação"))
        return NodeOutput.single(out)


# ---------------------------------------------------------------- connectors


class _CapabilityConfig(BaseModel):
    capacidade: str = Field(..., min_length=1)
    parametros: dict = Field(default_factory=dict)


class CapabilityNode(Node):
    """Invoke one of the owner's curated API capabilities, by name.

    Preferred over a raw `http` node for third-party APIs: the URL, the method and
    the secret all live in the connector registry, so the workflow never carries
    them.
    """

    metadata = NodeMetadata(
        type="capacidade", name="Chamar capacidade", category="kernel",
        description="Executa uma capacidade de API cadastrada pelo dono.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _CapabilityConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        connectors = context.services.require("connectors")
        cfg = self.config
        with context.session() as db:
            out = await connectors.invoke(
                db, context.owner_id, cfg.capacidade, cfg.parametros
            )
        if not out.get("ok"):
            raise RuntimeError(
                f"capacidade '{cfg.capacidade}' falhou: {out.get('error') or out.get('status')}"
            )
        return NodeOutput.single({"status": out.get("status"), "dados": out.get("data")})


# ---------------------------------------------------------------- goals / life


class _GoalConfig(BaseModel):
    titulo: str = Field(..., min_length=1)
    descricao: str | None = None
    prioridade: int = Field(default=2, ge=0, le=5)


class CreateGoalNode(Node):
    """Create a goal in the Planning Engine."""

    metadata = NodeMetadata(
        type="meta_criar", name="Criar meta", category="kernel",
        description="Cria um objetivo no motor de planejamento.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _GoalConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        planning = context.services.require("planning")
        cfg = self.config
        with context.session() as db:
            goal = await planning.create_goal(
                db, context.owner_id, cfg.titulo,
                description=cfg.descricao, priority=cfg.prioridade,
            )
            return NodeOutput.single(
                {"id": goal.id, "titulo": goal.title, "status": goal.status}
            )


class _ListGoalsConfig(BaseModel):
    status: str | None = None                 # pending|active|blocked|done|cancelled


class ListGoalsNode(Node):
    """List goals; emits one item per goal."""

    metadata = NodeMetadata(
        type="meta_listar", name="Listar metas", category="kernel",
        description="Emite as metas do dono (opcionalmente filtradas por status).",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _ListGoalsConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        planning = context.services.require("planning")
        with context.session() as db:
            goals = planning.list_goals(db, context.owner_id, self.config.status)
            items = [
                {"id": g.id, "titulo": g.title, "status": g.status,
                 "prioridade": g.priority, "progresso": g.progress,
                 "prazo": g.due_at.isoformat() if g.due_at else None}
                for g in goals
            ]
        return NodeOutput(items={"main": items})


class _BriefingConfig(BaseModel):
    tipo: Literal["daily", "on_demand"] = "on_demand"


class BriefingNode(Node):
    """Generate a briefing — the woven report of present, goals, focus and lessons."""

    metadata = NodeMetadata(
        type="briefing", name="Gerar briefing", category="kernel",
        description="Produz o relatório do segundo cérebro.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _BriefingConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        briefing = context.services.require("briefing")
        with context.session() as db:
            report = await briefing.generate(db, context.owner_id, kind=self.config.tipo)
            return NodeOutput.single(
                {"id": report.id, "resumo": report.summary, "tipo": report.kind}
            )


class _JournalConfig(BaseModel):
    conteudo: str = Field(..., min_length=1)
    humor: str | None = None


class JournalNode(Node):
    """Write a dated entry in the owner's journal."""

    metadata = NodeMetadata(
        type="diario_escrever", name="Escrever no diário", category="kernel",
        description="Adiciona uma entrada datada ao diário do dono.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _JournalConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        journal = context.services.require("journal")
        cfg = self.config
        with context.session() as db:
            entry = await journal.add(db, context.owner_id, cfg.conteudo, mood=cfg.humor)
            return NodeOutput.single({"id": entry.id, "conteudo": entry.content})


class _LearningConfig(BaseModel):
    contexto: str = Field(..., min_length=1)
    observacao: str | None = None
    licao: str | None = None
    qualidade: float = Field(default=0.5, ge=0.0, le=1.0)
    tag: str | None = None


class LearningNode(Node):
    """Register a lesson so the kernel behaves better next time."""

    metadata = NodeMetadata(
        type="aprender", name="Registrar aprendizado", category="kernel",
        description="Grava a lição de um resultado observado.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _LearningConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        learning = context.services.require("learning")
        cfg = self.config
        with context.session() as db:
            entry = await learning.record(
                db, context.owner_id, cfg.contexto, observation=cfg.observacao,
                quality=cfg.qualidade, lesson=cfg.licao, tag=cfg.tag, source="teia",
            )
            return NodeOutput.single({"id": entry.id, "qualidade": entry.quality})


class _DecideConfig(BaseModel):
    pergunta: Literal["proxima_meta"] = "proxima_meta"


class DecideNode(Node):
    """Ask the Decision Engine what to focus on now."""

    metadata = NodeMetadata(
        type="decidir", name="Decidir", category="kernel",
        description="Escolhe o próximo foco, com a justificativa.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _DecideConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        decision = context.services.require("decision")
        with context.session() as db:
            chosen = await decision.decide_next_goal(db, context.owner_id)
        if not chosen:
            return NodeOutput(items={"main": []})
        return NodeOutput.single({
            "id": chosen.id, "escolha": chosen.chosen_label,
            "justificativa": chosen.rationale,
        })


KERNEL_NODES = [
    RememberNode, RecallNode,
    WorldSetNode, WorldGetNode, OwnerAttributeNode,
    PublishEventNode, ScheduleNode,
    NotifyNode, DeviceActionNode, CapabilityNode,
    CreateGoalNode, ListGoalsNode, BriefingNode,
    JournalNode, LearningNode, DecideNode,
]
