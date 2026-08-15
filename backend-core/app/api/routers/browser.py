"""
Browser — the kernel's own reach into the web, measured and kept.

  GET    /api/v1/browser/tabs         web searches the kernel performed (this boot)
  GET    /api/v1/browser/marks        saved links (kind=bookmark, live in Memory)
  POST   /api/v1/browser/marks        save a link (201)
  DELETE /api/v1/browser/marks/{id}   unsave a link

The kernel does not control a browser — it has no tabs to read out of Chrome
and no bookmarks to import. What it HAS is its own window into the web: the
searches the owner runs through it, kept since boot (its "tabs"), and links
the owner decides are worth keeping. A kept link literally becomes a memory
node of kind `bookmark` — so Browser·Marks is the memory graph wearing a
browser costume, and everything else in the HUD (recall, graph, purge) already
knows how to treat it.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.memory import PersistentMemory
from app.browser.activity import recent_tabs
from app.core.di import get_memory
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/browser", tags=["browser"])


class MarkRequest(BaseModel):
    url: str = Field(..., min_length=4, description="Link a guardar")
    title: str = Field(..., min_length=1, description="Título do marcador")


def _mark_out(m) -> dict:
    return {
        "id": m.id,
        "title": m.title or m.content,
        "url": m.content,  # the bookmark's content IS the url
        "created_at": m.created_at,
    }


@router.get("/tabs")
async def browser_tabs(owner: Owner = Depends(get_current_owner)) -> dict:
    """The kernel's searches since boot — ephemeral, honest about it."""
    tabs, started_at = recent_tabs()
    return {"tabs": tabs, "count": len(tabs), "session_started_at": started_at}


@router.get("/marks")
async def list_marks(
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    marks = [_mark_out(m) for m in memory.list_all(db, owner.id, 200) if m.kind == "bookmark"]
    return {"marks": marks, "count": len(marks)}


@router.post("/marks", status_code=status.HTTP_201_CREATED)
async def add_mark(
    body: MarkRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    """Save a link. It is a memory of kind `bookmark` — the graph owns it."""
    m = await memory.remember(db, owner.id, body.url, "bookmark", 0.6, title=body.title)
    return _mark_out(m)


@router.delete("/marks/{mark_id}")
async def delete_mark(
    mark_id: str,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    if not memory.forget(db, owner.id, mark_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marcador não encontrado")
    return {"forgotten": mark_id}
