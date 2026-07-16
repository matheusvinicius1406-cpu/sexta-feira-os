"""
ORM models for the private local kernel.

Model of the world:
  * ONE Owner (single-owner product).
  * MANY Devices paired to that owner (phone, car, glasses, watch...).
  * Conversations -> Messages (persisted chat history).
  * Memory entries (the semantic second brain, with locally-computed embeddings).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    A durable fact the brain remembers about you — the second brain.
    Embeddings are computed LOCALLY (Ollama) and stored as JSON text so
    retrieval survives restarts. Nothing leaves the machine.
    """
    __tablename__ = "memories"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owner.id", ondelete="CASCADE"), index=True, nullable=False)
    content = Column(Text, nullable=False)
    kind = Column(String, default="fact")              # fact|preference|person|routine|note
    importance = Column(Float, default=0.5)            # 0.0 - 1.0
    embedding = Column(Text, nullable=True)            # JSON-encoded vector
    source = Column(String, default="manual")          # manual|auto_learned|imported
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now, index=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
