"""
Memory and context endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas.schemas import MemoryEntryRequest, MemoryEntryResponse, MemoryContextResponse
from app.models.models import User
from app.auth.jwt import get_user_id_from_token
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


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


@router.get("/", response_model=MemoryContextResponse)
async def get_memory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's memory and context"""
    context = MemoryService.get_user_context(db, current_user.id)
    
    return MemoryContextResponse(
        user_context=context.get("memory", {}),
        recent_interactions=context.get("recent_interactions", []),
        preferences=context.get("preferences", {})
    )


@router.post("/entry", response_model=MemoryEntryResponse)
async def create_memory_entry(
    entry_data: MemoryEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update a memory entry"""
    entry = MemoryService.update_memory_entry(
        db=db,
        user_id=current_user.id,
        key=entry_data.key,
        value=entry_data.value,
        category=entry_data.category
    )
    
    return MemoryEntryResponse(
        id=entry.id,
        key=entry.key,
        value=entry.value,
        category=entry.category,
        importance=entry.importance,
        created_at=entry.created_at,
        updated_at=entry.updated_at
    )
