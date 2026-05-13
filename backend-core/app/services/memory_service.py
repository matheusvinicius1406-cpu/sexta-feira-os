"""
Memory and context management service
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import MemoryEntry, User, ChatMessage
import uuid
import logging

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing user memory and context"""
    
    @staticmethod
    def create_memory_entry(
        db: Session,
        user_id: str,
        key: str,
        value: str,
        category: str = "general",
        importance: int = 0
    ) -> MemoryEntry:
        """Create a new memory entry"""
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            importance=importance
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    
    @staticmethod
    def get_user_memory(db: Session, user_id: str) -> Dict[str, Any]:
        """Get all memory entries for a user"""
        entries = db.query(MemoryEntry).filter(
            MemoryEntry.user_id == user_id
        ).all()
        
        memory_dict = {}
        for entry in entries:
            if entry.category not in memory_dict:
                memory_dict[entry.category] = {}
            memory_dict[entry.category][entry.key] = {
                "value": entry.value,
                "importance": entry.importance,
                "updated": entry.updated_at.isoformat()
            }
        
        return memory_dict
    
    @staticmethod
    def update_memory_entry(
        db: Session,
        user_id: str,
        key: str,
        value: str,
        category: str = "general"
    ) -> Optional[MemoryEntry]:
        """Update or create a memory entry"""
        entry = db.query(MemoryEntry).filter(
            MemoryEntry.user_id == user_id,
            MemoryEntry.key == key,
            MemoryEntry.category == category
        ).first()
        
        if entry:
            entry.value = value
            db.commit()
            db.refresh(entry)
        else:
            entry = MemoryService.create_memory_entry(
                db, user_id, key, value, category
            )
        
        return entry
    
    @staticmethod
    def get_user_context(db: Session, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context for AI processing"""
        # Get memory
        memory = MemoryService.get_user_memory(db, user_id)
        
        # Get recent interactions
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        recent_interactions = [msg.content for msg in recent_messages]
        
        # Build context
        context = {
            "user_id": user_id,
            "memory": memory,
            "recent_interactions": recent_interactions,
            "preferences": memory.get("preferences", {}),
            "habits": memory.get("habits", {})
        }
        
        return context
    
    @staticmethod
    def store_interaction(
        db: Session,
        user_id: str,
        message: str,
        is_assistant: bool,
        provider: str = "openai"
    ) -> None:
        """Store a chat interaction for memory"""
        # TODO: Extract key information from message and store as memory
        pass
