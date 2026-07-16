"""
Automations — the kernel's hands, via a local n8n.

  GET  /api/v1/automations/status     is n8n reachable?
  GET  /api/v1/automations            list your workflows
  POST /api/v1/automations/trigger    fire a workflow by its webhook path
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.jwt import get_current_owner
from app.automation.n8n import AutomationUnavailable, N8nClient
from app.core.di import get_automations
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
