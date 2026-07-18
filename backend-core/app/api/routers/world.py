"""
World Model & User Model — inspect and curate the Kernel's sense of NOW and of
its owner. Sovereign curation: the owner can read, set and forget any of it.

  GET    /api/v1/world                 the present (world facts)
  POST   /api/v1/world                 set/update a world fact (upsert by key)
  GET    /api/v1/world/profile         the owner model (user attributes)
  POST   /api/v1/world/profile         set/update a user attribute (upsert by key)
  GET    /api/v1/world/digest          the compact digest the Kernel injects
  DELETE /api/v1/world/profile/{key}   forget a user attribute
  DELETE /api/v1/world/{key}           forget a world fact
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_world
from app.db.database import get_db
from app.models.models import Owner
from app.world.service import WorldModel

router = APIRouter(prefix="/api/v1/world", tags=["world"])


class FactRequest(BaseModel):
    key: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    category: str = "other"
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    is_inference: bool = False


def _fact_out(row) -> dict:
    return {
        "id": row.id, "key": row.key, "value": row.value, "category": row.category,
        "source": row.source, "confidence": row.confidence,
        "is_inference": row.is_inference, "updated_at": row.updated_at,
    }


# ---- world facts (the present) ----

@router.get("")
def snapshot(
    limit: int = 200,
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    return [_fact_out(f) for f in world.snapshot(db, owner.id, limit)]


@router.post("")
def set_fact(
    body: FactRequest,
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    f = world.set_fact(
        db, owner.id, body.key, body.value, category=body.category,
        source="owner", confidence=body.confidence, is_inference=body.is_inference,
    )
    return _fact_out(f)


# ---- user attributes (the owner over time) — declared before /{key} ----

@router.get("/profile")
def profile(
    limit: int = 200,
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    return [_fact_out(a) for a in world.profile(db, owner.id, limit)]


@router.post("/profile")
def set_attribute(
    body: FactRequest,
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    a = world.set_attribute(
        db, owner.id, body.key, body.value, category=body.category,
        source="owner", confidence=body.confidence, is_inference=body.is_inference,
    )
    return _fact_out(a)


@router.get("/digest")
def digest(
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    return {"digest": world.context_digest(db, owner.id)}


@router.delete("/profile/{key}")
def forget_attribute(
    key: str,
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    if not world.forget_attribute(db, owner.id, key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atributo não encontrado")
    return {"forgotten": key}


@router.delete("/{key}")
def forget_fact(
    key: str,
    owner: Owner = Depends(get_current_owner),
    world: WorldModel = Depends(get_world),
    db: Session = Depends(get_db),
):
    if not world.forget_fact(db, owner.id, key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fato não encontrado")
    return {"forgotten": key}
