"""
Jarvis System API endpoints
Exposes the enhanced AI assistant capabilities
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import User
from app.auth.jwt import get_user_id_from_token
from app.ai.orchestrator import ai_orchestrator
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/v1/jarvis", tags=["jarvis"])


# Request/Response models
class JarvisMessage(BaseModel):
    message: str
    provider: Optional[str] = "gemini"
    context: Optional[dict] = None


class JarvisResponse(BaseModel):
    response: str
    provider: str
    confidence: float
    metadata: dict


class JarvisStatus(BaseModel):
    status: str
    version: str
    providers: list
    default_provider: str
    features: dict


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


@router.get("/status", response_model=JarvisStatus)
async def get_jarvis_status():
    """Get Jarvis system status"""
    providers = ai_orchestrator.get_available_providers()
    
    return JarvisStatus(
        status="operational",
        version="1.0.0",
        providers=providers,
        default_provider=ai_orchestrator.default_provider,
        features={
            "gemini_integration": True,
            "memory_system": True,
            "learning_enabled": True,
            "tool_support": True,
            "multi_agent": True,
        }
    )


@router.post("/chat", response_model=JarvisResponse)
async def jarvis_chat(
    request: JarvisMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with Jarvis AI assistant
    Enhanced endpoint with Gemini integration and context awareness
    """
    try:
        # Get user context from memory
        user_context = MemoryService.get_user_context(db, current_user.id)
        
        # Build agent prompt with user info
        agent_prompt = f"""You are Jarvis, a personal AI assistant for {current_user.name}.
        
Your goal is to be helpful, intelligent, and personalized to the user's needs and preferences.
Always consider the user's context and history when responding.
Be concise but thorough in your responses."""
        
        # Process through AI orchestrator
        response = await ai_orchestrator.process_chat(
            message=request.message,
            provider=request.provider or "gemini",
            context=user_context
        )
        
        return JarvisResponse(
            response=response.get("response", "No response"),
            provider=response.get("provider", "unknown"),
            confidence=response.get("confidence", 0.0),
            metadata=response.get("metadata", {})
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )


@router.post("/analyze")
async def jarvis_analyze(
    text: str,
    analysis_type: str = "general",
    current_user: User = Depends(get_current_user),
):
    """
    Analyze text using Jarvis
    Supports: sentiment, summary, keywords, general
    """
    try:
        from app.jarvis import GeminiOrchestratorV2
        import os
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not configured")
        
        orchestrator = GeminiOrchestratorV2(api_key)
        result = await orchestrator.analyze_text(text, analysis_type)
        
        return {
            "analysis": result.get("response"),
            "type": analysis_type,
            "provider": result.get("provider"),
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing text: {str(e)}"
        )


@router.get("/providers")
async def get_providers():
    """Get available AI providers"""
    return {
        "providers": ai_orchestrator.get_available_providers(),
        "default": ai_orchestrator.default_provider,
    }


@router.post("/memory/store")
async def store_memory(
    key: str,
    value: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store something in Jarvis memory"""
    try:
        MemoryService.create_memory_entry(
            db=db,
            user_id=current_user.id,
            key=key,
            value=value,
            category="jarvis"
        )
        return {
            "status": "stored",
            "key": key,
            "timestamp": str(__import__("datetime").datetime.utcnow().isoformat())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error storing memory: {str(e)}"
        )


@router.get("/memory/recall")
async def recall_memory(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recall from Jarvis memory"""
    try:
        memory = MemoryService.get_user_memory(db, current_user.id)
        
        # Search for key in all categories
        for category, entries in memory.items():
            if key in entries:
                return {
                    "key": key,
                    "value": entries[key]["value"],
                    "category": category,
                    "updated": entries[key]["updated"]
                }
        
        return {"key": key, "value": None, "found": False}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recalling memory: {str(e)}"
        )
