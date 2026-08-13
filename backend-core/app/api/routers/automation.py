"""
Automations — the kernel's hands, running on the Teia (ADR-0013).

  GET    /api/v1/automations/status               engine health
  GET    /api/v1/automations                      list your automations
  POST   /api/v1/automations                      create / update one
  POST   /api/v1/automations/validate             check a graph without saving
  POST   /api/v1/automations/run                  run by slug
  GET    /api/v1/automations/executions           the audit trail
  GET    /api/v1/automations/executions/{id}      one run, node by node
  POST   /api/v1/automations/executions/{id}/cancel
  GET    /api/v1/automations/types                every node and trigger type
  POST   /api/v1/automations/catalog/install      install the built-in automations
  POST   /api/v1/automations/webhook/{caminho}    fire a webhook-triggered automation
  GET    /api/v1/automations/{slug}               one automation, with its graph
  POST   /api/v1/automations/{slug}/run           run it
  POST   /api/v1/automations/{slug}/enable        turn it on/off
  DELETE /api/v1/automations/{slug}               remove it

Everything runs in this process, on this machine. There is no external workflow
runtime to reach, so "offline" is not a state this API can be in.
"""
from typing import Any

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.automation.teia import catalog
from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine.errors import WorkflowNotFound
from app.automation.teia.service import TeiaService
from app.core.di import get_automations
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])


# ---------------------------------------------------------------- schemas


class SaveRequest(BaseModel):
    """A workflow graph, as JSON (`definicao`) or as YAML text (`yaml`)."""

    slug: str | None = Field(default=None, description="nome estável; padrão: do título")
    descricao: str | None = None
    ativo: bool = True
    tags: list[str] = Field(default_factory=list)
    definicao: dict[str, Any] | None = None
    yaml: str | None = None


class RunRequest(BaseModel):
    automacao: str = Field(..., min_length=1, description="slug da automação")
    dados: dict[str, Any] = Field(default_factory=dict)


class EnableRequest(BaseModel):
    ativo: bool


def _to_workflow(body: SaveRequest) -> Workflow:
    if body.definicao is None and not body.yaml:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "envie 'definicao' (JSON do grafo) ou 'yaml'",
        )
    try:
        if body.yaml:
            data = yaml.safe_load(body.yaml)
            if not isinstance(data, dict):
                raise ValueError("o YAML não descreve um workflow")
            return Workflow.model_validate(data)
        return Workflow.model_validate(body.definicao)
    except (ValueError, TypeError) as e:
        # Only the FIRST problem line, truncated — the full pydantic traceback
        # leaked internal schema details (field paths, library versions) to
        # anyone who could reach the API.
        first = str(e).splitlines()[0][:160] if str(e) else "workflow inválido"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"grafo inválido: {first}") from e


def _result_or_error(result) -> dict:
    return result.to_dict()


# ---------------------------------------------------------------- engine


@router.get("/status")
async def automations_status(
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
):
    return await teia.status()


@router.get("/types")
async def automation_types(
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
):
    """Every node and trigger type available, with their config schemas."""
    return {"nodes": teia.node_types(), "triggers": teia.trigger_types()}


# ---------------------------------------------------------------- CRUD


@router.get("")
async def list_automations(
    busca: str | None = None,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    return teia.list(db, owner.id, query=busca)


@router.post("", status_code=status.HTTP_201_CREATED)
async def save_automation(
    body: SaveRequest,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    workflow = _to_workflow(body)
    try:
        row = teia.save(
            db, owner.id, workflow, slug=body.slug, description=body.descricao,
            enabled=body.ativo, tags=body.tags,
        )
    except WorkflowValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"erro": "workflow inválido", "problemas": e.problems},
        ) from e
    return teia.store.to_dict(row, include_definition=True)


@router.post("/validate")
async def validate_automation(
    body: SaveRequest,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
):
    """Check a graph without saving it — what the editor calls while you type."""
    workflow = _to_workflow(body)
    problems = teia.validate(workflow)
    return {"valido": not problems, "problemas": problems, "nos": len(workflow.nodes)}


# ---------------------------------------------------------------- running


@router.post("/run")
async def run_automation(
    body: RunRequest,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
):
    try:
        result = await teia.run_slug(owner.id, body.automacao, body.dados)
    except WorkflowNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return _result_or_error(result)


# ---------------------------------------------------------------- executions


@router.get("/executions")
async def list_executions(
    automacao: str | None = None,
    limite: int = 50,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    rows = teia.executions.list(db, owner.id, slug=automacao, limit=min(limite, 200))
    return [teia.executions.to_dict(r) for r in rows]


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    found = teia.executions.get(db, owner.id, execution_id)
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "execução não encontrada")
    return found


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
):
    if not teia.cancel(execution_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "essa execução não está rodando agora"
        )
    return {"ok": True, "execution_id": execution_id, "status": "cancelando"}


# ---------------------------------------------------------------- catalog


@router.post("/catalog/install")
async def install_catalog(
    sobrescrever: bool = False,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    """Install the built-in automations. Your own edits are never overwritten."""
    installed = catalog.seed(teia, db, owner.id, overwrite=sobrescrever)
    return {"instaladas": installed, "total": len(installed)}


# ---------------------------------------------------------------- webhooks


@router.post("/webhook/{caminho}")
async def fire_webhook(
    caminho: str,
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
    teia: TeiaService = Depends(get_automations),
):
    """Fire a webhook-triggered automation.

    No owner token: this is the entry point meant for other programs on your
    machine. The owner comes from the armed trigger, and a trigger that declares
    a `segredo` requires it in `X-Teia-Secret`.
    """
    armed = teia.triggers.find_webhook(caminho)
    if not armed:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"nenhuma automação ativa escuta o webhook '{caminho}'",
        )

    expected = str(armed.config.get("segredo") or "")
    if expected and request.headers.get("x-teia-secret", "") != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Teia-Secret inválido")

    result = await teia.run_slug(
        armed.owner_id, armed.slug, payload or {}, trigger_type="webhook"
    )
    return _result_or_error(result)


# ---------------------------------------------------------------- by slug
# Declared last so they never shadow /executions, /types or /catalog.


@router.get("/{slug}")
async def get_automation(
    slug: str,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    found = teia.get(db, owner.id, slug)
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"automação '{slug}' não existe")
    return found


@router.post("/{slug}/run")
async def run_automation_by_slug(
    slug: str,
    dados: dict[str, Any] = Body(default_factory=dict),
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
):
    try:
        result = await teia.run_slug(owner.id, slug, dados)
    except WorkflowNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return _result_or_error(result)


@router.post("/{slug}/enable")
async def enable_automation(
    slug: str,
    body: EnableRequest,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    if not teia.set_enabled(db, owner.id, slug, body.ativo):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"automação '{slug}' não existe")
    return {"ok": True, "slug": slug, "ativo": body.ativo}


@router.delete("/{slug}")
async def delete_automation(
    slug: str,
    owner: Owner = Depends(get_current_owner),
    teia: TeiaService = Depends(get_automations),
    db: Session = Depends(get_db),
):
    if not teia.delete(db, owner.id, slug):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"automação '{slug}' não existe")
    return {"ok": True, "slug": slug}
