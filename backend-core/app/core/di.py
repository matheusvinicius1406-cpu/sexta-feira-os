"""
Dependency Injection - Initialize and wire all components
"""
import logging
from typing import Optional

from app.core.config import settings
from app.infrastructure.ai.providers import AIProviderType
from app.infrastructure.ai.orchestrator import AIOrchestrator, ProviderFactory
from app.infrastructure.ai.tools import create_default_tool_executor
from app.infrastructure.memory.semantic import (
    EmbeddingService, InMemoryStore, RetrievalPipeline
)
from app.application.use_cases.conversation import ConversationPipeline
from app.infrastructure.voice.audio import AudioPipeline

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Central service container for dependency injection"""
    
    def __init__(self):
        self.ai_orchestrator: Optional[AIOrchestrator] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.memory_store: Optional[InMemoryStore] = None
        self.retrieval_pipeline: Optional[RetrievalPipeline] = None
        self.conversation_pipeline: Optional[ConversationPipeline] = None
        self.tool_executor = None
        self.audio_pipeline: Optional[AudioPipeline] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all services"""
        if self._initialized:
            logger.info("Services already initialized")
            return
        
        logger.info("Initializing service container...")
        
        # 1. Initialize embedding service
        logger.info("Initializing embedding service...")
        self.embedding_service = EmbeddingService()
        await self.embedding_service.initialize()
        
        # 2. Initialize memory store
        logger.info("Initializing memory store...")
        self.memory_store = InMemoryStore(self.embedding_service)
        
        # 3. Initialize retrieval pipeline
        logger.info("Initializing retrieval pipeline...")
        self.retrieval_pipeline = RetrievalPipeline(
            self.memory_store,
            self.embedding_service
        )
        
        # 4. Initialize tool executor
        logger.info("Initializing tool executor...")
        self.tool_executor = create_default_tool_executor()
        
        # 4.5. Initialize audio pipeline
        logger.info("Initializing audio pipeline...")
        self.audio_pipeline = AudioPipeline()
        await self.audio_pipeline.initialize()
        
        # 5. Initialize AI Orchestrator with providers
        logger.info("Initializing AI orchestrator...")
        self.ai_orchestrator = self._create_ai_orchestrator()
        
        # 6. Initialize conversation pipeline
        logger.info("Initializing conversation pipeline...")
        from app.infrastructure.repositories.conversation import SQLConversationRepository
        from app.db.database import SessionLocal
        
        # For now, use in-memory. In production, use SQLConversationRepository
        class InMemoryConversationRepository:
            async def create_session(self, user_id, metadata=None):
                from app.application.use_cases.conversation import ConversationSession
                from datetime import datetime
                import uuid
                return ConversationSession(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    messages=[],
                    metadata=metadata or {}
                )
            
            async def get_session(self, conversation_id, user_id):
                return None
            
            async def save_session(self, session):
                pass
            
            async def list_conversations(self, user_id, limit=20):
                return []
        
        self.conversation_pipeline = ConversationPipeline(
            ai_orchestrator=self.ai_orchestrator,
            memory_service=self.retrieval_pipeline,
            conversation_repository=InMemoryConversationRepository()
        )
        
        self._initialized = True
        logger.info("✅ All services initialized successfully")
    
    def _create_ai_orchestrator(self) -> AIOrchestrator:
        """Create and configure AI orchestrator with providers"""
        providers = []
        
        # Primary provider
        primary_type = AIProviderType(settings.default_ai_provider)
        
        if primary_type == AIProviderType.GEMINI and settings.gemini_api_key:
            primary = ProviderFactory.create_provider(
                AIProviderType.GEMINI,
                api_key=settings.gemini_api_key,
                model=settings.ai_model_gemini
            )
        elif primary_type == AIProviderType.OPENAI and settings.openai_api_key:
            primary = ProviderFactory.create_provider(
                AIProviderType.OPENAI,
                api_key=settings.openai_api_key,
                model=settings.ai_model_openai
            )
        elif primary_type == AIProviderType.CLAUDE and settings.claude_api_key:
            primary = ProviderFactory.create_provider(
                AIProviderType.CLAUDE,
                api_key=settings.claude_api_key,
                model=settings.ai_model_claude
            )
        elif primary_type == AIProviderType.OLLAMA and settings.ollama_endpoint:
            primary = ProviderFactory.create_provider(
                AIProviderType.OLLAMA,
                endpoint=settings.ollama_endpoint
            )
        else:
            raise ValueError(f"Primary provider {primary_type} not configured")
        
        logger.info(f"Primary provider: {primary_type.value}")
        
        # Fallback providers
        fallback = []
        
        if settings.openai_api_key and primary_type != AIProviderType.OPENAI:
            fallback.append(ProviderFactory.create_provider(
                AIProviderType.OPENAI,
                api_key=settings.openai_api_key,
                model=settings.ai_model_openai
            ))
            logger.info("Added OpenAI as fallback")
        
        if settings.claude_api_key and primary_type != AIProviderType.CLAUDE:
            fallback.append(ProviderFactory.create_provider(
                AIProviderType.CLAUDE,
                api_key=settings.claude_api_key,
                model=settings.ai_model_claude
            ))
            logger.info("Added Claude as fallback")
        
        if settings.ollama_endpoint and primary_type != AIProviderType.OLLAMA:
            fallback.append(ProviderFactory.create_provider(
                AIProviderType.OLLAMA,
                endpoint=settings.ollama_endpoint
            ))
            logger.info("Added Ollama as fallback")
        
        orchestrator = AIOrchestrator(
            default_provider=primary,
            fallback_providers=fallback
        )
        
        return orchestrator
    
    async def health_check(self) -> dict:
        """Check service health"""
        health = {
            "initialized": self._initialized,
            "embedding_service": "ok" if self.embedding_service else "offline",
            "memory_store": "ok" if self.memory_store else "offline",
            "ai_orchestrator": "unknown"
        }
        
        if self.ai_orchestrator:
            try:
                if await self.ai_orchestrator.default_provider.health_check():
                    health["ai_orchestrator"] = "ok"
                else:
                    health["ai_orchestrator"] = "unhealthy"
            except Exception as e:
                health["ai_orchestrator"] = f"error: {e}"
        
        return health


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get or create global service container"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


async def initialize_services() -> None:
    """Initialize all services (call from app startup)"""
    container = get_container()
    await container.initialize()


def get_conversation_pipeline() -> ConversationPipeline:
    """Get conversation pipeline for dependency injection"""
    container = get_container()
    if not container.conversation_pipeline:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return container.conversation_pipeline


def get_ai_orchestrator() -> AIOrchestrator:
    """Get AI orchestrator for dependency injection"""
    container = get_container()
    if not container.ai_orchestrator:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return container.ai_orchestrator
