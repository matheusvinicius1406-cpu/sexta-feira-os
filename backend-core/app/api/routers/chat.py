"""
Chat and assistant endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import uuid
from typing import Optional
from app.db.database import get_db
from app.schemas.schemas import ChatRequest, ChatMessageResponse, ConversationResponse
from app.models.models import ChatMessage, User
from app.auth.jwt import get_user_id_from_token
from app.ai.orchestrator import ai_orchestrator
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current user from token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
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


@router.post("/", response_model=ChatMessageResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the assistant"""
    
    # Get user context for AI processing
    context = MemoryService.get_user_context(db, current_user.id)
    
    # Process through AI orchestrator
    ai_response = await ai_orchestrator.process_chat(
        message=request.message,
        provider=request.provider or "openai",
        context=context
    )
    
    # Store assistant response in database
    response_msg = ChatMessage(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        content=ai_response["response"],
        is_from_assistant=True,
        ai_provider=ai_response.get("provider", "openai"),
        confidence=ai_response.get("confidence", 0.0)
    )
    
    db.add(response_msg)
    db.commit()
    db.refresh(response_msg)
    
    return ChatMessageResponse(
        id=response_msg.id,
        content=response_msg.content,
        is_from_assistant=response_msg.is_from_assistant,
        ai_provider=response_msg.ai_provider,
        confidence=response_msg.confidence,
        created_at=response_msg.created_at
    )


@router.get("/history", response_model=ConversationResponse)
async def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history for current user"""
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    return ConversationResponse(
        messages=[
            ChatMessageResponse(
                id=msg.id,
                content=msg.content,
                is_from_assistant=msg.is_from_assistant,
                ai_provider=msg.ai_provider,
                confidence=msg.confidence,
                created_at=msg.created_at
            )
            for msg in messages
        ],
        total_count=len(messages)
    )
