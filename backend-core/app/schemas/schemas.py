"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ Auth Schemas ============

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    expires_in: int


class UserCreate(BaseModel):
    """User creation schema"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str


class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Chat Schemas ============

class ChatRequest(BaseModel):
    """Chat/message request schema"""
    message: str = Field(..., min_length=1, max_length=2000)
    provider: Optional[str] = Field(default="openai", description="AI provider to use")
    context: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """Chat message response schema"""
    id: str
    content: str
    is_from_assistant: bool
    ai_provider: str
    confidence: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Conversation/history response"""
    messages: List[ChatMessageResponse]
    total_count: int


# ============ Memory Schemas ============

class MemoryEntryRequest(BaseModel):
    """Memory entry creation request"""
    key: str
    value: str
    category: Optional[str] = "general"
    importance: Optional[int] = Field(default=0, ge=0, le=10)


class MemoryEntryResponse(BaseModel):
    """Memory entry response"""
    id: str
    key: str
    value: str
    category: str
    importance: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MemoryContextResponse(BaseModel):
    """User context/memory response"""
    user_context: Dict[str, Any]
    recent_interactions: List[str]
    preferences: Dict[str, Any]


# ============ Health & Status Schemas ============

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    database: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    status_code: int
