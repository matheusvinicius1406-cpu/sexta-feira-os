"""
SQL Implementation of Conversation Repository
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import Base
from app.application.use_cases.conversation import (
    ConversationRepository, ConversationSession, ConversationMessage, MessageRole
)

logger = logging.getLogger(__name__)


class ConversationModel(Base):
    """SQLAlchemy model for conversations"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSON, default={})
    title = Column(String, nullable=True)
    
    @classmethod
    def from_session(cls, session: ConversationSession):
        """Convert ConversationSession to model"""
        return cls(
            id=session.id,
            user_id=session.user_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            meta_data=session.metadata,
            title=session.metadata.get("title")
        )


class MessageModel(Base):
    """SQLAlchemy model for conversation messages"""
    __tablename__ = "conversation_messages"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tokens = Column(Integer, default=0)
    meta_data = Column(JSON, default={})


class SQLConversationRepository(ConversationRepository):
    """SQL implementation of ConversationRepository"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_session(
        self,
        user_id: str,
        metadata: Dict[str, Any] = None
    ) -> ConversationSession:
        """Create new conversation session"""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = ConversationSession(
            id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            messages=[],
            metadata=metadata or {}
        )
        
        # Persist to DB
        db_model = ConversationModel.from_session(session)
        self.db.add(db_model)
        await self.db.commit()
        
        logger.info(f"Created conversation session: {session_id}")
        return session
    
    async def get_session(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[ConversationSession]:
        """Retrieve conversation session"""
        # Get conversation
        stmt = select(ConversationModel).filter(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        conv_model = result.scalar_one_or_none()
        
        if not conv_model:
            return None
        
        # Get messages
        stmt = select(MessageModel).filter(
            MessageModel.conversation_id == conversation_id
        ).order_by(MessageModel.timestamp)
        result = await self.db.execute(stmt)
        msg_models = result.scalars().all()
        
        # Convert to domain models
        messages = [
            ConversationMessage(
                id=m.id,
                role=MessageRole(m.role),
                content=m.content,
                timestamp=m.timestamp,
                metadata=m.meta_data or {}
            )
            for m in msg_models
        ]
        
        return ConversationSession(
            id=conv_model.id,
            user_id=conv_model.user_id,
            created_at=conv_model.created_at,
            updated_at=conv_model.updated_at,
            messages=messages,
            metadata=conv_model.meta_data or {}
        )
    
    async def save_session(self, session: ConversationSession) -> None:
        """Persist conversation session"""
        # Update conversation
        stmt = select(ConversationModel).filter(
            ConversationModel.id == session.id
        )
        result = await self.db.execute(stmt)
        conv_model = result.scalar_one_or_none()
        
        if not conv_model:
            conv_model = ConversationModel.from_session(session)
            self.db.add(conv_model)
        else:
            conv_model.updated_at = datetime.utcnow()
            conv_model.meta_data = session.metadata
        
        await self.db.commit()
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: MessageRole,
        content: str
    ) -> Optional[ConversationMessage]:
        """Add message to conversation"""
        # Verify conversation belongs to user
        stmt = select(ConversationModel).filter(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        conv_model = result.scalar_one_or_none()
        
        if not conv_model:
            return None
        
        # Create message
        msg_id = str(uuid.uuid4())
        msg_model = MessageModel(
            id=msg_id,
            conversation_id=conversation_id,
            role=role.value,
            content=content,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(msg_model)
        conv_model.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return ConversationMessage(
            id=msg_id,
            role=role,
            content=content,
            timestamp=msg_model.timestamp
        )
    
    async def list_conversations(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[ConversationSession]:
        """List user's conversations"""
        stmt = select(ConversationModel).filter(
            ConversationModel.user_id == user_id
        ).order_by(ConversationModel.updated_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        conv_models = result.scalars().all()
        
        sessions = []
        for conv_model in conv_models:
            session = await self.get_session(conv_model.id, user_id)
            if session:
                sessions.append(session)
        
        return sessions
