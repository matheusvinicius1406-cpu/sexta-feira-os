"""
Memory System - Semantic storage and retrieval with embeddings
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Memory item structure"""
    id: str
    user_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    memory_type: str = "general"  # general, fact, preference, experience
    importance: float = 0.5  # 0.0-1.0
    access_count: int = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class EmbeddingService:
    """Generates embeddings for semantic search"""
    
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model
        self.model = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize embedding model (lazy loading)"""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self._initialized = True
            logger.info(f"Embedding model loaded: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed, using mock embeddings")
            self._initialized = False
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self._initialized:
            await self.initialize()
        
        if self.model is None:
            # Mock embedding for testing
            return [float(ord(c) % 256) / 256 for c in text[:384]]
        
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self._initialized:
            await self.initialize()
        
        if self.model is None:
            return [await self.embed_text(t) for t in texts]
        
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return [e.tolist() for e in embeddings]
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class MemoryStore:
    """Abstract memory store interface"""
    
    async def store(self, memory: Memory) -> str:
        """Store a memory, return ID"""
        raise NotImplementedError
    
    async def retrieve(self, memory_id: str, user_id: str) -> Optional[Memory]:
        """Retrieve a specific memory"""
        raise NotImplementedError
    
    async def search(
        self,
        user_id: str,
        query: str,
        embedding: Optional[List[float]] = None,
        limit: int = 5,
        memory_type: Optional[str] = None
    ) -> List[Memory]:
        """Search memories semantically"""
        raise NotImplementedError
    
    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory"""
        raise NotImplementedError
    
    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Memory]:
        """List user's memories"""
        raise NotImplementedError


class InMemoryStore(MemoryStore):
    """In-memory memory store (for development)"""
    
    def __init__(self, embedding_service: EmbeddingService):
        self.memories: Dict[str, Memory] = {}
        self.embedding_service = embedding_service
    
    async def store(self, memory: Memory) -> str:
        """Store memory"""
        if not memory.embedding and memory.content:
            memory.embedding = await self.embedding_service.embed_text(memory.content)
        
        self.memories[memory.id] = memory
        logger.info(f"Memory stored: {memory.id}")
        return memory.id
    
    async def retrieve(self, memory_id: str, user_id: str) -> Optional[Memory]:
        """Retrieve memory"""
        memory = self.memories.get(memory_id)
        if memory and memory.user_id == user_id:
            memory.access_count += 1
            return memory
        return None
    
    async def search(
        self,
        user_id: str,
        query: str,
        embedding: Optional[List[float]] = None,
        limit: int = 5,
        memory_type: Optional[str] = None
    ) -> List[Memory]:
        """Search memories semantically"""
        if embedding is None:
            embedding = await self.embedding_service.embed_text(query)
        
        # Filter and score
        matches = []
        for mem in self.memories.values():
            if mem.user_id != user_id:
                continue
            if memory_type and mem.memory_type != memory_type:
                continue
            if not mem.embedding:
                continue
            
            score = self.embedding_service.cosine_similarity(embedding, mem.embedding)
            matches.append((mem, score))
        
        # Sort by score and importance
        matches.sort(key=lambda x: (x[1], x[0].importance), reverse=True)
        
        return [m[0] for m in matches[:limit]]
    
    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete memory"""
        memory = self.memories.get(memory_id)
        if memory and memory.user_id == user_id:
            del self.memories[memory_id]
            return True
        return False
    
    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Memory]:
        """List user's memories"""
        result = [
            m for m in self.memories.values()
            if m.user_id == user_id and (not memory_type or m.memory_type == memory_type)
        ]
        return result[:limit]


class RetrievalPipeline:
    """Pipeline for memory retrieval and ranking"""
    
    def __init__(self, memory_store: MemoryStore, embedding_service: EmbeddingService):
        self.memory_store = memory_store
        self.embedding_service = embedding_service
    
    async def retrieve_for_context(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Memory]:
        """Retrieve memories for conversation context"""
        embedding = await self.embedding_service.embed_text(query)
        memories = await self.memory_store.search(
            user_id=user_id,
            query=query,
            embedding=embedding,
            limit=limit
        )
        
        # Increase access count
        for mem in memories:
            mem.access_count += 1
        
        return memories
    
    async def retrieve_conversation_history(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 10
    ) -> List[Memory]:
        """Retrieve conversation history"""
        memories = await self.memory_store.list_memories(
            user_id=user_id,
            memory_type="conversation",
            limit=limit * 2  # Get more to filter
        )
        
        # Filter by conversation_id in metadata
        result = [
            m for m in memories
            if m.metadata.get("conversation_id") == conversation_id
        ]
        
        return result[-limit:]  # Return last N


class ConversationCompressor:
    """Compress old conversations into summaries"""
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
    
    async def compress_conversation(
        self,
        messages: List[Dict[str, str]],
        user_id: str
    ) -> Memory:
        """Compress conversation into summary memory"""
        # Create summary from messages
        summary_parts = []
        for msg in messages[-10:]:  # Last 10 messages
            summary_parts.append(f"{msg['role']}: {msg['content'][:100]}")
        
        summary = " | ".join(summary_parts)
        
        # Create memory
        memory = Memory(
            id=f"compressed_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            content=summary,
            memory_type="compressed_conversation",
            importance=0.7,
            metadata={"original_messages": len(messages)}
        )
        
        # Embed
        memory.embedding = await self.embedding_service.embed_text(summary)
        
        return memory
