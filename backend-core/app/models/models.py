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
