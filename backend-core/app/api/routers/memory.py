"""
Memory — inspect and curate your second brain directly. Teach it facts,
review what it knows, and forget what you want gone.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.memory import PersistentMemory
from app.core.di import get_memory
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


class RememberRequest(BaseModel):
    content: str = Field(..., min_length=1)
    kind: str = "fact"
    importance: float = Field(0.5, ge=0.0, le=1.0)


class RecallRequest(BaseModel):
    query: str
    top_k: Optional[int] = None


@router.post("")
async def remember(
    body: RememberRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    m = await memory.remember(db, owner.id, body.content, body.kind, body.importance)
    return {"id": m.id, "content": m.content, "kind": m.kind}


@router.post("/recall")
async def recall(
    body: RecallRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    results = await memory.recall(db, owner.id, body.query, body.top_k)
    return [{"id": m.id, "content": m.content, "kind": m.kind} for m in results]


@router.get("")
async def list_memories(
    limit: int = 200,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": m.id, "content": m.content, "kind": m.kind,
            "importance": m.importance, "source": m.source, "created_at": m.created_at,
        }
        for m in memory.list_all(db, owner.id, limit)
    ]


@router.delete("/{memory_id}")
async def forget(
    memory_id: str,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    if not memory.forget(db, owner.id, memory_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memória não encontrada")
    return {"forgotten": memory_id}
