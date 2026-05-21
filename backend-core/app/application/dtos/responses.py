"""
DTOs (Data Transfer Objects) for API contracts
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Chat DTOs ============

class ChatMessageRequest(BaseModel):
    """Chat message request"""
    content: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    stream: bool = False
    prompt_type: str = "default"


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: str
    role: str
    content: str
    timestamp: datetime


class ConversationResponse(BaseModel):
    """Conversation response"""
    id: str
    messages: List[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}


class StreamingChatRequest(BaseModel):
    """Request for streaming chat"""
    content: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    stream_id: Optional[str] = None
    prompt_type: str = "default"


# ============ Memory DTOs ============

class MemoryStoreRequest(BaseModel):
    """Request to store memory"""
    content: str = Field(..., min_length=1, max_length=5000)
    memory_type: str = "general"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}


class MemorySearchRequest(BaseModel):
    """Request to search memories"""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(5, ge=1, le=20)
    memory_type: Optional[str] = None


class MemoryResponse(BaseModel):
    """Memory response"""
    id: str
    content: str
    memory_type: str
    importance: float
    created_at: datetime
    metadata: Dict[str, Any] = {}


# ============ AI Gateway DTOs ============

class AIProviderStatus(BaseModel):
    """AI provider status"""
    provider: str
    available: bool
    model: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class AIGatewayStatus(BaseModel):
    """AI Gateway status"""
    default_provider: str
    providers: List[AIProviderStatus]
    routing_strategy: str


# ============ Jarvis DTOs ============

class JarvisStatus(BaseModel):
    """Jarvis system status"""
    status: str  # online, offline, maintenance
    version: str
    uptime_seconds: float
    ai_gateway: AIGatewayStatus
    memory_available: bool
    active_conversations: int


class JarvisAnalyzeRequest(BaseModel):
    """Request for Jarvis analysis"""
    text: str = Field(..., min_length=1, max_length=5000)
    analysis_type: str = "general"


class JarvisAnalyzeResponse(BaseModel):
    """Jarvis analysis response"""
    analysis_type: str
    summary: str
    key_points: List[str]
    sentiment: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ============ Automation DTOs ============

class AutomationTaskRequest(BaseModel):
    """Request to create automation task"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=5000)
    task_type: str  # reminder, trigger, workflow
    schedule: Optional[str] = None  # cron format
    enabled: bool = True
    metadata: Dict[str, Any] = {}


class AutomationTaskResponse(BaseModel):
    """Automation task response"""
    id: str
    name: str
    task_type: str
    enabled: bool
    created_at: datetime
    last_executed: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


# ============ Health & Status DTOs ============

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    services: Dict[str, str]
    version: str
