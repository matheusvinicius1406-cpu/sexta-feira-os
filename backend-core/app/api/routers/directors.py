"""
Directors — the permanent specialist cabinet (Agent System).

  GET  /api/v1/directors                    list the cabinet (seeds defaults)
  POST /api/v1/directors                    create/update a custom director
  GET  /api/v1/directors/{name}/memory      the director's accumulated expertise
  POST /api/v1/directors/{name}/memory      teach the director something
  POST /api/v1/directors/{name}/delegate    delegate a task (runs on the local brain)
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.engine import BrainUnavailable
from app.core.di import get_directors
from app.db.database import get_db
from app.directors.service import DirectorService
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/directors", tags=["directors"])


class DirectorRequest(BaseModel):
    name: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    allowed_tools: list[str] | None = None


class TeachRequest(BaseModel):
    content: str = Field(..., min_length=1)
    importance: float = Field(0.6, ge=0.0, le=1.0)


class DelegateRequest(BaseModel):
    task: str = Field(..., min_length=1)


def _director_out(d) -> dict:
    return {
        "id": d.id, "name": d.name, "title": d.title, "domain": d.domain,
        "allowed_tools": json.loads(d.allowed_tools) if d.allowed_tools else None,
        "enabled": d.enabled, "created_at": d.created_at,
    }


@router.get("")
def list_directors(
    owner: Owner = Depends(get_current_owner),
    directors: DirectorService = Depends(get_directors),
    db: Session = Depends(get_db),
):
    directors.ensure_defaults(db, owner.id)
    return [_director_out(d) for d in directors.list(db, owner.id)]


@router.post("")
def create_director(
    body: DirectorRequest,
    owner: Owner = Depends(get_current_owner),
    directors: DirectorService = Depends(get_directors),
    db: Session = Depends(get_db),
):
    d = directors.create(
        db, owner.id, body.name, body.title, body.domain, body.allowed_tools
    )
    return _director_out(d)


@router.get("/{name}/memory")
def expertise(
    name: str,
    limit: int = 50,
    owner: Owner = Depends(get_current_owner),
    directors: DirectorService = Depends(get_directors),
    db: Session = Depends(get_db),
):
    if not directors.get(db, owner.id, name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diretor não encontrado")
    return [
        {"id": m.id, "content": m.content, "importance": m.importance, "created_at": m.created_at}
        for m in directors.expertise(db, owner.id, name, limit)
    ]


@router.post("/{name}/memory")
async def teach(
    name: str,
    body: TeachRequest,
    owner: Owner = Depends(get_current_owner),
    directors: DirectorService = Depends(get_directors),
    db: Session = Depends(get_db),
):
    if not directors.get(db, owner.id, name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diretor não encontrado")
    await directors.teach(db, owner.id, name, body.content, body.importance)
    return {"taught": name}


@router.post("/{name}/delegate")
async def delegate(
    name: str,
    body: DelegateRequest,
    owner: Owner = Depends(get_current_owner),
    directors: DirectorService = Depends(get_directors),
    db: Session = Depends(get_db),
):
    try:
        result = await directors.delegate(db, owner.id, name, body.task)
    except BrainUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    return {"director": name, "result": result}
