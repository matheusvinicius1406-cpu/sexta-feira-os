"""
Jarvis AI Assistant API - Production implementation
Handles Android ↔ Gemini integration with memory context
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, AsyncIterator
from pydantic import BaseModel
import logging
import json

from app.db.database import get_db
from app.models.models import User
from app.auth.jwt import get_user_id_from_token
from app.core.di import get_ai_orchestrator
from app.infrastructure.ai.providers import AIRequest, AIMessage
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/jarvis", tags=["jarvis"])


# ========== Data Models ==========

class JarvisMessage(BaseModel):
    """Chat message from Android"""
    message: str
    conversation_id: Optional[str] = None
    stream: bool = False


class JarvisResponse(BaseModel):
    """Chat response to Android"""
    response: str
    provider: str
    conversation_id: Optional[str] = None
    metadata: dict = {}


class JarvisStatus(BaseModel):
    """Jarvis system status"""
    status: str
    version: str
    gemini_ready: bool
    memory_ready: bool


# ========== Dependencies ==========

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract user from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    token = authorization.split(" ")[1]
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


# ========== Endpoints ==========

@router.get("/status", response_model=JarvisStatus)
async def jarvis_status(
    current_user: User = Depends(get_current_user)
):
    """Get Jarvis operational status"""
    orchestrator = get_ai_orchestrator()
    
    return JarvisStatus(
        status="operational",
        version="1.0.0",
        gemini_ready=orchestrator.default_provider is not None,
        memory_ready=True
    )


@router.post("/chat", response_model=JarvisResponse)
async def jarvis_chat(
    request: JarvisMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with Jarvis (non-streaming)
    
    Sends message → Gemini → Returns response with memory integration
    """
    try:
        orchestrator = get_ai_orchestrator()
        
        # Build AI request
        ai_request = AIRequest(
            messages=[AIMessage(role="user", content=request.message)],
            model="gemini-2.0-flash",
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        # Generate response via orchestrator
        response = await orchestrator.generate(
            ai_request,
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            prompt_type="default"
        )
        
        logger.info(f"Jarvis response generated for user {current_user.id}")
        
        return JarvisResponse(
            response=response.content,
            provider=response.provider,
            conversation_id=request.conversation_id,
            metadata={
                "model": response.model,
                "tokens": response.tokens_used
            }
        )
    
    except Exception as e:
        logger.error(f"Jarvis chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )


@router.post("/chat/stream")
async def jarvis_chat_stream(
    request: JarvisMessage,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with Jarvis (streaming)
    
    Streams responses token-by-token to Android
    """
    async def stream_response() -> AsyncIterator[str]:
        try:
            orchestrator = get_ai_orchestrator()
            
            # Build AI request
            ai_request = AIRequest(
                messages=[AIMessage(role="user", content=request.message)],
                model="gemini-2.0-flash",
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )
            
            # Stream from orchestrator
            async for chunk in orchestrator.stream_generate(
                ai_request,
                user_id=current_user.id,
                conversation_id=request.conversation_id,
                prompt_type="default"
            ):
                # Send each chunk as SSE
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Send completion marker
            yield f"data: {json.dumps({'done': True})}\n\n"
            logger.info(f"Jarvis stream completed for user {current_user.id}")
            
        except Exception as e:
            logger.error(f"Jarvis stream error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )


@router.post("/memory/save")
async def save_memory(
    key: str,
    value: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save user memory entry (for context future chats)"""
    try:
        memory_service = MemoryService(db)
        await memory_service.store(
            user_id=current_user.id,
            content=value,
            metadata={"key": key}
        )
        return {"status": "saved", "key": key}
    except Exception as e:
        logger.error(f"Memory save error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save memory: {str(e)}"
        )


@router.get("/memory/retrieve")
async def retrieve_memory(
    query: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve relevant memory entries for context"""
    try:
        memory_service = MemoryService(db)
        memories = await memory_service.retrieve(
            user_id=current_user.id,
            query=query,
            limit=limit
        )
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Memory retrieve error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}"
        )
