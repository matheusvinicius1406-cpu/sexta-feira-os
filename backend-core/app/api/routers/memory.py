"""
Memory — inspect and curate your second brain, now as a KNOWLEDGE GRAPH.

  POST   /api/v1/memory              teach a fact (auto-links to related nodes)
  POST   /api/v1/memory/recall       networked recall (semantic + graph expansion)
  GET    /api/v1/memory              list nodes
  DELETE /api/v1/memory/{id}         forget a node (its edges cascade)
  POST   /api/v1/memory/{id}/link    connect two nodes by hand
  DELETE /api/v1/memory/links/{id}   remove an edge
  GET    /api/v1/memory/{id}/neighbours   links + backlinks of a node
  GET    /api/v1/memory/graph        the whole graph (nodes + edges) to visualize
"""

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
    title: str | None = None
    kind: str = "fact"
    importance: float = Field(0.5, ge=0.0, le=1.0)


class RecallRequest(BaseModel):
    query: str
    top_k: int | None = None
    networked: bool = True  # expand along links; False = plain semantic


class LinkRequest(BaseModel):
    target_id: str
    relation: str = "related"
    weight: float = 1.0


# ---- static routes BEFORE dynamic /{id} routes ----

@router.post("")
async def remember(
    body: RememberRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    m = await memory.remember(
        db, owner.id, body.content, body.kind, body.importance, title=body.title
    )
    return {"id": m.id, "title": m.title, "content": m.content, "kind": m.kind}


@router.post("/recall")
async def recall(
    body: RecallRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    fn = memory.recall_graph if body.networked else memory.recall
    results = await fn(db, owner.id, body.query, body.top_k)
    return [{"id": m.id, "title": m.title, "content": m.content, "kind": m.kind} for m in results]


@router.get("")
async def list_memories(
    limit: int = 200,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": m.id, "title": m.title, "content": m.content, "kind": m.kind,
            "importance": m.importance, "source": m.source, "created_at": m.created_at,
        }
        for m in memory.list_all(db, owner.id, limit)
    ]


@router.get("/graph")
async def graph(
    limit: int = 500,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    return memory.graph(db, owner.id, limit)


@router.delete("/links/{link_id}")
async def unlink(
    link_id: str,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    if not memory.unlink(db, owner.id, link_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ligação não encontrada")
    return {"unlinked": link_id}


@router.post("/{memory_id}/link")
async def link(
    memory_id: str,
    body: LinkRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    edge = memory.link(
        db, owner.id, memory_id, body.target_id,
        relation=body.relation, weight=body.weight, origin="manual",
    )
    if not edge:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não foi possível criar a ligação")
    return {"id": edge.id, "source": edge.source_id, "target": edge.target_id,
            "relation": edge.relation, "weight": edge.weight}


@router.get("/{memory_id}/neighbours")
async def neighbours(
    memory_id: str,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    return memory.neighbours(db, owner.id, memory_id)


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
