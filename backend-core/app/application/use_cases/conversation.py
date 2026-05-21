"""
Conversation Pipeline - End-to-end message processing
"""
from typing import Optional, Dict, Any, List, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ConversationMessage:
    """Message in a conversation"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API"""
        if self.metadata is None:
            self.metadata = {}
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ConversationSession:
    """Conversation session with user"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessage]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def add_message(self, role: MessageRole, content: str) -> ConversationMessage:
        """Add message to session"""
        msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg
    
    def get_last_n_messages(self, n: int = 10) -> List[ConversationMessage]:
        """Get last N messages for context"""
        return self.messages[-n:]
    
    def to_openai_format(self) -> List[Dict[str, str]]:
        """Convert to OpenAI message format"""
        return [
            {"role": m.role.value, "content": m.content}
            for m in self.messages
        ]


class ConversationRepository:
    """Abstract repository for persisting conversations"""
    
    async def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> ConversationSession:
        """Create new conversation session"""
        raise NotImplementedError
    
    async def get_session(self, conversation_id: str, user_id: str) -> Optional[ConversationSession]:
        """Retrieve conversation session"""
        raise NotImplementedError
    
    async def save_session(self, session: ConversationSession) -> None:
        """Persist conversation session"""
        raise NotImplementedError
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: MessageRole,
        content: str
    ) -> ConversationMessage:
        """Add message to conversation"""
        raise NotImplementedError


class MessageContextBuilder:
    """Builds context for each message"""
    
    def __init__(self, memory_service=None):
        self.memory_service = memory_service
    
    async def build_context(
        self,
        session: ConversationSession,
        include_memory: bool = True
    ) -> Dict[str, Any]:
        """Build message context"""
        context = {
            "session_id": session.id,
            "user_id": session.user_id,
            "conversation_history": session.get_last_n_messages(10),
            "created_at": session.created_at,
            "metadata": session.metadata,
        }
        
        # Add memories
        if include_memory and self.memory_service and len(session.messages) > 0:
            last_msg = session.messages[-1].content
            try:
                memories = await self.memory_service.retrieve_for_context(
                    session.user_id,
                    last_msg,
                    limit=5
                )
                context["relevant_memories"] = memories
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")
                context["relevant_memories"] = []
        
        return context


class ConversationPipeline:
    """Main pipeline for processing conversations"""
    
    def __init__(
        self,
        ai_orchestrator,
        memory_service,
        conversation_repository: Optional[ConversationRepository] = None
    ):
        self.ai_orchestrator = ai_orchestrator
        self.memory_service = memory_service
        self.conversation_repository = conversation_repository
        self.context_builder = MessageContextBuilder(memory_service)
    
    async def process_message(
        self,
        user_id: str,
        conversation_id: Optional[str],
        message_content: str,
        prompt_type: str = "default",
        stream: bool = False
    ):
        """Process user message end-to-end"""
        # 1. Get or create session
        if conversation_id:
            session = await self.conversation_repository.get_session(conversation_id, user_id)
        else:
            session = await self.conversation_repository.create_session(user_id)
        
        # 2. Add user message
        user_msg = session.add_message(MessageRole.USER, message_content)
        
        # 3. Build context
        context = await self.context_builder.build_context(session)
        
        # 4. Build AI request
        from app.infrastructure.ai.providers import AIMessage, AIRequest
        
        messages = [
            AIMessage(
                role=m.role.value,
                content=m.content,
                metadata=m.metadata or {}
            )
            for m in session.get_last_n_messages(20)
        ]
        
        ai_request = AIRequest(
            messages=messages,
            model=self.ai_orchestrator.default_provider.model,
            temperature=0.7,
            max_tokens=2000,
            stream=stream,
            metadata=context
        )
        
        # 5. Generate response
        if stream:
            return await self._stream_response(
                session, ai_request, user_id, prompt_type
            )
        else:
            return await self._generate_response(
                session, ai_request, user_id, prompt_type
            )
    
    async def _generate_response(
        self,
        session: ConversationSession,
        ai_request,
        user_id: str,
        prompt_type: str
    ) -> Dict[str, Any]:
        """Generate non-streaming response"""
        try:
            # Get AI response
            response = await self.ai_orchestrator.generate(
                ai_request,
                user_id=user_id,
                conversation_id=session.id,
                prompt_type=prompt_type
            )
            
            # Add assistant message
            assistant_msg = session.add_message(
                MessageRole.ASSISTANT,
                response.content
            )
            
            # Save session
            if self.conversation_repository:
                await self.conversation_repository.save_session(session)
            
            return {
                "success": True,
                "conversation_id": session.id,
                "message": assistant_msg.to_dict(),
                "metadata": {
                    "provider": response.provider,
                    "model": response.model,
                    "tokens_used": response.tokens_used,
                    "stop_reason": response.stop_reason
                }
            }
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "success": False,
                "error": str(e),
                "conversation_id": session.id
            }
    
    async def _stream_response(
        self,
        session: ConversationSession,
        ai_request,
        user_id: str,
        prompt_type: str
    ):
        """Generate streaming response"""
        full_content = ""
        
        try:
            # Stream AI response
            async for chunk in self.ai_orchestrator.stream_generate(
                ai_request,
                user_id=user_id,
                conversation_id=session.id,
                prompt_type=prompt_type
            ):
                full_content += chunk
                yield {
                    "type": "token",
                    "content": chunk,
                    "conversation_id": session.id
                }
            
            # Add assistant message
            assistant_msg = session.add_message(
                MessageRole.ASSISTANT,
                full_content
            )
            
            # Save session
            if self.conversation_repository:
                await self.conversation_repository.save_session(session)
            
            yield {
                "type": "complete",
                "message": assistant_msg.to_dict(),
                "conversation_id": session.id
            }
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "conversation_id": session.id
            }
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[ConversationSession]:
        """Retrieve conversation"""
        if not self.conversation_repository:
            return None
        return await self.conversation_repository.get_session(conversation_id, user_id)
    
    async def list_conversations(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[ConversationSession]:
        """List user's conversations"""
        if not self.conversation_repository:
            return []
        return await self.conversation_repository.list_conversations(user_id, limit)
