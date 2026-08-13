"""
Connectors — the API capability system. Define once, the brain executes anytime.

Capabilities (owner-defined API calls):
  POST   /api/v1/connectors                 create/update a capability
  GET    /api/v1/connectors[?query=]        list/search capabilities
  GET    /api/v1/connectors/{name}          full spec of one
  DELETE /api/v1/connectors/{name}          remove one
  POST   /api/v1/connectors/{name}/call     invoke it now (test)

Secrets (encrypted at rest — values are never returned):
  POST   /api/v1/connectors/secrets         set a secret {name, value}
  GET    /api/v1/connectors/secrets         list secret NAMES only
  DELETE /api/v1/connectors/secrets/{name}  delete a secret
"""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner, get_current_owner_strict
from app.connectors.service import ConnectorService
from app.core.di import get_connectors
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


class CapabilitySpec(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    category: str = "general"
    method: str = "GET"
    url: str = Field(..., min_length=1)
    query: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    body: Any | None = None
    params_schema: list[dict[str, Any]] | None = None
    enabled: bool = True


class CallRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class SecretRequest(BaseModel):
    name: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


# ---------- capabilities ----------

@router.post("")
async def upsert(
    spec: CapabilitySpec,
    owner: Owner = Depends(get_current_owner),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    cap = connectors.upsert_capability(db, owner.id, spec.model_dump())
    return {"name": cap.name, "enabled": cap.enabled}


@router.get("")
async def list_capabilities(
    query: str | None = None,
    owner: Owner = Depends(get_current_owner),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    return connectors.list_capabilities(db, owner.id, query)


# ---------- secrets (declared before /{name} so 'secrets' isn't captured) ----------

# The secrets vault uses get_current_owner_strict: with the dev auth bypass on,
# ANY local process can read everything — except here. The owner's API keys are
# the one thing that must never be readable by a process that did not present a
# real token.
@router.post("/secrets")
async def set_secret(
    body: SecretRequest,
    owner: Owner = Depends(get_current_owner_strict),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    connectors.set_secret(db, owner.id, body.name, body.value)
    return {"ok": True, "name": body.name}   # value never echoed


@router.get("/secrets")
async def list_secrets(
    owner: Owner = Depends(get_current_owner_strict),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    return {"names": connectors.list_secret_names(db, owner.id)}


@router.delete("/secrets/{secret_name}")
async def delete_secret(
    secret_name: str,
    owner: Owner = Depends(get_current_owner_strict),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    if not connectors.delete_secret(db, owner.id, secret_name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Segredo não encontrado")
    return {"deleted": secret_name}


@router.post("/{name}/call")
async def call(
    name: str,
    body: CallRequest,
    owner: Owner = Depends(get_current_owner),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    return await connectors.invoke(db, owner.id, name, body.params)


@router.get("/{name}")
async def get_one(
    name: str,
    owner: Owner = Depends(get_current_owner),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    cap = connectors.get(db, owner.id, name)
    if not cap:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Capacidade não encontrada")
    return {
        "name": cap.name, "description": cap.description, "category": cap.category,
        "method": cap.method, "url": cap.url,
        "query": json.loads(cap.query) if cap.query else None,
        "headers": json.loads(cap.headers) if cap.headers else None,
        "body": json.loads(cap.body) if cap.body else None,
        "params_schema": json.loads(cap.params_schema) if cap.params_schema else None,
        "enabled": cap.enabled,
    }


@router.delete("/{name}")
async def delete(
    name: str,
    owner: Owner = Depends(get_current_owner),
    connectors: ConnectorService = Depends(get_connectors),
    db: Session = Depends(get_db),
):
    if not connectors.delete_capability(db, owner.id, name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Capacidade não encontrada")
    return {"deleted": name}
