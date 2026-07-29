"""
Automations — the kernel's hands, via a local n8n.

  GET  /api/v1/automations/status          is n8n reachable?
  GET  /api/v1/automations                 list your workflows
  POST /api/v1/automations/trigger         fire a workflow by its webhook path
  POST /api/v1/automations/callback        n8n -> Kernel bidirectional bridge
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.automation.callback import CallbackHandler, CallbackRequest
from app.automation.n8n import AutomationUnavailable, N8nClient
from app.core.config import settings
from app.core.di import get_automations, get_kernel
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])


class TriggerRequest(BaseModel):
    webhook: str = Field(..., min_length=1, description="the Webhook node path")
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
async def automations_status(
    owner: Owner = Depends(get_current_owner),
    n8n: N8nClient = Depends(get_automations),
):
    return await n8n.status()


@router.get("")
async def list_automations(
    owner: Owner = Depends(get_current_owner),
    n8n: N8nClient = Depends(get_automations),
):
    try:
        return await n8n.list_workflows()
    except AutomationUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/trigger")
async def trigger_automation(
    body: TriggerRequest,
    owner: Owner = Depends(get_current_owner),
    n8n: N8nClient = Depends(get_automations),
):
    try:
        return await n8n.trigger(body.webhook, body.payload)
    except AutomationUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


# ====================================================================
# n8n -> Kernel callback bridge
# ====================================================================
#
# This endpoint lets n8n workflows CALL BACK into the kernel to query
# memory, publish events, read world state, dispatch device actions, and
# more. It is the bidirectional half of the n8n integration.
#
# Authentication: X-N8N-Callback-Secret header (must match .env)
#
# Body: { "action": "...", "params": { ... } }
#
# Actions:
#   recall       -> search memory
#   remember     -> save to memory
#   event        -> publish event
#   world        -> read world model state
#   world_set    -> set world model fact
#   schedule     -> schedule reminder/action
#   action       -> dispatch device action
#   capabilities -> list API capabilities
#   call_api     -> execute API capability
#   health       -> ping the kernel
# ====================================================================


@router.post("/callback")
async def n8n_callback(
    body: CallbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Validate callback secret
    secret = request.headers.get("x-n8n-callback-secret", "")
    if not settings.n8n_callback_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "N8N_CALLBACK_SECRET não configurado no .env. Gere um com: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'",
        )
    if secret != settings.n8n_callback_secret:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "X-N8N-Callback-Secret inválido. Verifique se o n8n está "
            "enviando o mesmo segredo configurado no .env",
        )

    try:
        handler = CallbackHandler(get_kernel())
        return await handler.handle(db, body.action, body.params or {})
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Callback {body.action} falhou: {e}",
        ) from e
