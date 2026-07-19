"""
ORM models for the private local kernel.

Model of the world:
  * ONE Owner (single-owner product).
  * MANY Devices paired to that owner (phone, car, glasses, watch...).
  * Conversations -> Messages (persisted chat history).
  * Memory entries (the semantic second brain, with locally-computed embeddings).
"""
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Owner(Base):
    """The one and only owner of this brain."""
    __tablename__ = "owner"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now)

    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")


class Device(Base):
    """A trusted body of the brain: phone, car screen, glasses, watch, laptop."""
    __tablename__ = "devices"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)              # "Meu Pixel", "Tela do carro"
    kind = Column(String, default="generic")           # phone|car|glasses|watch|desktop|generic
    paired_at = Column(DateTime, default=_now)
    last_seen_at = Column(DateTime, default=_now)
    revoked = Column(Boolean, default=False, nullable=False)

    owner = relationship("Owner", back_populates="devices")


class Conversation(Base):
    """A thread of dialogue with the brain."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=True)
    device_id = Column(String, nullable=True)          # which body started it
    created_at = Column(DateTime, default=_now, index=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    messages = relationship(
        "Message", back_populates="conversation",
        cascade="all, delete-orphan", order_by="Message.created_at",
    )


class Message(Base):
    """A single turn inside a conversation."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role = Column(String, nullable=False)              # "owner" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now, index=True)

    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base):
    """
    A NODE in the knowledge graph — a durable thing the brain remembers.
    Nodes connect to each other via MemoryLink edges, forming a networked
    second brain (à la Obsidian). Embeddings are computed LOCALLY (Ollama)
    and stored as JSON text so retrieval survives restarts.
    """
    __tablename__ = "memories"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=True, index=True)  # short label; wikilink target
    content = Column(Text, nullable=False)
    kind = Column(String, default="fact")              # fact|preference|person|routine|note|concept
    importance = Column(Float, default=0.5)            # 0.0 - 1.0
    embedding = Column(Text, nullable=True)            # JSON-encoded vector
    source = Column(String, default="manual")          # manual|auto_learned|imported|wikilink
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now, index=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class MemoryLink(Base):
    """
    An EDGE between two memory nodes — a connection in the brain.
    Links are directed but traversed both ways (backlinks). They arise from
    [[wikilinks]], semantic similarity, LLM relation extraction, or by hand.
    """
    __tablename__ = "memory_links"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    source_id = Column(String, ForeignKey("memories.id", ondelete="CASCADE"), index=True, nullable=False)
    target_id = Column(String, ForeignKey("memories.id", ondelete="CASCADE"), index=True, nullable=False)
    relation = Column(String, default="related")       # related|wikilink|is_a|part_of|about|...
    weight = Column(Float, default=1.0)                 # strength of the connection
    origin = Column(String, default="semantic")        # semantic|wikilink|manual|llm
    created_at = Column(DateTime, default=_now)


class DeviceCommand(Base):
    """
    An ACTION the brain dispatched to a body (phone/computer/car...) to execute.
    The kernel is a transport: it carries {action, params} to the device; the
    device defines what each action means. Fire-and-forget, with a persisted queue
    so a briefly-offline device still picks up its commands on reconnect.
    """
    __tablename__ = "device_commands"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    device_id = Column(String, ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    action = Column(String, nullable=False)            # "open_app" | "call" | "navigate" | ...
    params = Column(Text, nullable=True)               # JSON-encoded arguments
    status = Column(String, default="pending", index=True)  # pending|delivered|done|failed
    result = Column(Text, nullable=True)               # JSON-encoded result from the device
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now, index=True)
    delivered_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ScheduledTask(Base):
    """
    A future intention: a reminder ("me lembre disso daqui a 2 meses") or a timed
    action ("navegar pra faculdade às 8h"). The scheduler fires it when due, using
    the Action Protocol. Optional recurrence reschedules it.
    """
    __tablename__ = "scheduled_tasks"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    kind = Column(String, default="reminder")          # "reminder" | "action"
    due_at = Column(DateTime, nullable=False, index=True)
    text = Column(Text, nullable=True)                 # reminder message
    device_selector = Column(String, nullable=True)    # target body ("celular"...)
    action = Column(String, nullable=True)             # for kind="action"
    params = Column(Text, nullable=True)               # JSON args
    recurrence_seconds = Column(Integer, nullable=True)  # repeat every N seconds
    status = Column(String, default="pending", index=True)  # pending|fired|cancelled
    created_at = Column(DateTime, default=_now, index=True)
    fired_at = Column(DateTime, nullable=True)


class Secret(Base):
    """
    An owner secret (API key/token), ENCRYPTED at rest (Fernet). Never returned by
    the API — only its name. This is what keeps 'é só meu' true for connectors.
    """
    __tablename__ = "secrets"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False, index=True)
    value_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class WorldFact(Base):
    """
    A single truth about the PRESENT — the living 'now' the Kernel consults on
    every decision (the World Model). Upserted by (owner, key), so there is one
    current value per key ("localizacao", "foco_atual", "dispositivos_online").
    Inferences (mood, energy) are flagged as such, never stated as hard fact.
    Distinct from Memory: memory keeps the past; the World Model keeps the now.
    """
    __tablename__ = "world_facts"
    __table_args__ = (UniqueConstraint("owner_id", "key", name="uq_world_facts_owner_key"),)

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    key = Column(String, nullable=False, index=True)          # canonical name of the fact
    value = Column(Text, nullable=False)                       # current value (text/JSON)
    category = Column(String, default="other", index=True)    # environment|user_state|active_work|goals|context|capabilities|other
    source = Column(String, default="kernel")                 # kernel|tool|device|owner|inferred
    confidence = Column(Float, default=1.0)                   # 0.0 - 1.0
    is_inference = Column(Boolean, default=False, nullable=False)  # inferred, not observed
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now, index=True)


class UserAttribute(Base):
    """
    A durable trait of the OWNER modelled over time (the User Model): goals,
    habits, preferences, study/coding style, recurring difficulties, projects.
    Upserted by (owner, key). Fed by memory and interactions so the brain
    understands its one owner deeply — always under 'só meu'.
    """
    __tablename__ = "user_attributes"
    __table_args__ = (UniqueConstraint("owner_id", "key", name="uq_user_attributes_owner_key"),)

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    key = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=False)
    category = Column(String, default="other", index=True)    # goals|habits|preferences|style|knowledge|social|projects|other
    source = Column(String, default="kernel")                 # kernel|tool|owner|inferred
    confidence = Column(Float, default=1.0)
    is_inference = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now, index=True)


class Goal(Base):
    """
    A GOAL the system works toward — the Planning Engine's unit. Goals have a
    priority, an optional deadline, progress, a history (via events), and can be
    decomposed into sub-goals (self-reference via parent_id). A goal is 'blocked'
    while any of its dependencies (GoalDependency) is not done.
    """
    __tablename__ = "goals"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    parent_id = Column(String, ForeignKey("goals.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=2, index=True)         # higher = more important
    status = Column(String, default="pending", index=True)   # pending|active|blocked|done|cancelled
    progress = Column(Float, default=0.0)                     # 0.0 - 1.0
    due_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=_now, index=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    completed_at = Column(DateTime, nullable=True)


class GoalDependency(Base):
    """A directed edge: `goal_id` depends on `depends_on_id` (must finish first)."""
    __tablename__ = "goal_dependencies"
    __table_args__ = (
        UniqueConstraint("goal_id", "depends_on_id", name="uq_goal_dep"),
    )

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    goal_id = Column(String, ForeignKey("goals.id", ondelete="CASCADE"), index=True, nullable=False)
    depends_on_id = Column(String, ForeignKey("goals.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime, default=_now)


class Decision(Base):
    """
    A DECISION the Decision Engine made — choosing among alternatives under
    constraints/policies. Persisted so we can always answer "por que o JARVIS
    fez X?": it records the question, the policy used, the chosen option, a
    human rationale and the full scored alternatives. Auditable by design.
    """
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    question = Column(String, nullable=False, index=True)     # e.g. "next_goal"
    policy = Column(String, default="default")               # which policy weighted the score
    chosen_id = Column(String, nullable=True)                # id of the chosen option (e.g. a goal)
    chosen_label = Column(String, nullable=True)
    rationale = Column(Text, nullable=True)                  # why, in plain words
    options = Column(Text, nullable=True)                    # JSON: the scored alternatives
    created_at = Column(DateTime, default=_now, index=True)


class Briefing(Base):
    """
    A BRIEFING — a proactive summary the second brain produces (daily or on
    demand). It weaves together the five pillars: the present (World Model),
    open goals (Planning), the decided focus (Decision), recent events and
    lessons (Learning). Persisted as a history of "morning reports".

    Concept adapted (our own code) from the local-first daily-briefing idea; the
    Kernel stays "só meu" — assembled from local data only. See ADR-0006.
    """
    __tablename__ = "briefings"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    kind = Column(String, default="on_demand", index=True)   # daily|on_demand
    summary = Column(Text, nullable=True)                    # short human-readable text
    content = Column(Text, nullable=True)                    # JSON: the structured sections
    created_at = Column(DateTime, default=_now, index=True)


class Learning(Base):
    """
    A LEARNING — the durable takeaway from an outcome (North Star: "Aprendizado
    Contínuo"). After acting, the system observes the result, evaluates its
    quality, and registers a lesson that feeds Memory and the User Model, so the
    Kernel behaves better next time. Ties to what produced it via `ref_id`
    (a decision/goal/event). Auditable trail of how the brain improved.

    Design of the trace -> learn -> evaluate loop is adapted (in our own code) from
    the Apache-2.0 OpenJarvis learning orchestrator; see ADR-0005.
    """
    __tablename__ = "learnings"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    kind = Column(String, default="outcome", index=True)     # outcome|feedback|correction|insight
    tag = Column(String, nullable=True, index=True)          # topic, for recurrence detection
    ref_id = Column(String, nullable=True)                   # linked decision/goal/event id
    context = Column(Text, nullable=False)                   # what was attempted / happened
    observation = Column(Text, nullable=True)                # the observed result
    quality = Column(Float, default=0.5)                     # 0.0 (bad) .. 1.0 (good)
    lesson = Column(Text, nullable=True)                     # the durable takeaway
    source = Column(String, default="kernel")
    created_at = Column(DateTime, default=_now, index=True)


class Event(Base):
    """
    An EVENT on the kernel's event bus — the Event-Driven backbone. Something that
    HAPPENED ('usuario.acordou', 'localizacao.mudou', 'agendamento.venceu'), from a
    source (device/sensor/scheduler/owner/kernel). Events are IMMUTABLE facts of the
    past: we persist them as a first-class audit trail, assign a per-owner sequence
    for ordering, and only ever update processing status — never the payload.
    Each event may update the World Model (via subscribers).
    """
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key", name="uq_events_owner_idem"),
    )

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    type = Column(String, nullable=False, index=True)         # dotted name: "localizacao.mudou"
    source = Column(String, default="kernel")                 # device:<id>|sensor|scheduler|owner|kernel
    payload = Column(Text, nullable=True)                     # JSON-encoded data
    correlation_id = Column(String, nullable=True, index=True)  # ties a flow together
    idempotency_key = Column(String, nullable=True)           # dedupe (unique per owner when set)
    sequence = Column(Integer, default=0, index=True)         # per-owner monotonic order
    status = Column(String, default="received", index=True)   # received|processed|failed
    error = Column(Text, nullable=True)                       # subscriber failures (still auditable)
    created_at = Column(DateTime, default=_now, index=True)
    processed_at = Column(DateTime, nullable=True)


class Capability(Base):
    """
    A CONNECTOR: one owner-defined API call the brain can invoke by name ("execute
    everything"). The brain never calls arbitrary URLs — only these curated
    capabilities — so there's no SSRF from prompt injection. Templates ({param},
    {secret:NAME}) are filled at call time; secrets come from the encrypted vault.
    """
    __tablename__ = "capabilities"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False, index=True)         # unique per owner
    description = Column(Text, nullable=False)
    category = Column(String, default="general")
    method = Column(String, default="GET")
    url = Column(Text, nullable=False)                        # may contain {param}
    query = Column(Text, nullable=True)                       # JSON dict of key->template
    headers = Column(Text, nullable=True)                     # JSON dict (may use {secret:NAME})
    body = Column(Text, nullable=True)                        # JSON template (for POST/PUT)
    params_schema = Column(Text, nullable=True)               # JSON list of {name,description,required}
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
