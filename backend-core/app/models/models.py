"""
SQLAlchemy ORM Models for Sexta-Feira OS
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class User(Base):
    """User model for authentication and profile"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chats = relationship("ChatMessage", back_populates="user")
    memory_entries = relationship("MemoryEntry", back_populates="user")


class ChatMessage(Base):
    """Chat message model for conversation history"""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    content = Column(Text)
    is_from_assistant = Column(Boolean, default=False)
    ai_provider = Column(String, default="openai")
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="chats")


class MemoryEntry(Base):
    """Memory/Context model for persistent user context"""
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    key = Column(String, index=True)
    value = Column(Text)
    category = Column(String, default="general")
    importance = Column(Integer, default=0)  # 0-10 scale
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="memory_entries")


class AutomationTask(Base):
    """Automation/Task model for scheduled tasks"""
    __tablename__ = "automation_tasks"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    trigger_type = Column(String)  # "schedule", "event", "manual"
    action = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
