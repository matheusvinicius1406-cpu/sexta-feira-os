"""n8n service: trigger and inspect automations (future-facing, guarded).

The repo already ships n8n workflows (``scripts/n8n-workflows``). This service is
the controlled bridge for agents to list workflows and fire webhooks once an n8n
instance is wired up. Configuration comes from the environment so nothing is
hard-coded: ``N8N_BASE_URL`` and ``N8N_API_KEY``. Triggering is gated behind the
``n8n.trigger`` capability and every fire is audited.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..core.context import ExecutionContext
from ..core.errors import FactoryError, ValidationError


class N8nError(FactoryError):
    code = "n8n_error"


class N8nService:
    def __init__(self, ctx: ExecutionContext, base_url: str | None = None, api_key: str | None = None) -> None:
        self.ctx = ctx
        self.base_url = (base_url or os.environ.get("N8N_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("N8N_API_KEY", "")

    def _require_configured(self) -> None:
        if not self.base_url:
            raise ValidationError(
                "n8n is not configured",
                detail={"set": ["N8N_BASE_URL", "N8N_API_KEY"]},
            )

    def _request(self, method: str, path: str, body: dict | None = None) -> object:
        self._require_configured()
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-N8N-API-KEY", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as exc:
            raise N8nError(f"n8n API {exc.code}", detail={"status": exc.code, "path": path}) from exc
        except urllib.error.URLError as exc:
            raise N8nError("n8n unreachable", detail={"reason": str(exc.reason)}) from exc

    def list_workflows(self) -> dict:
        self.ctx.authorize("n8n.read", "workflows")
        data = self._request("GET", "/api/v1/workflows")
        items = [
            {"id": w.get("id"), "name": w.get("name"), "active": w.get("active")}
            for w in (data or {}).get("data", [])
        ]
        return {"count": len(items), "workflows": items}

    def trigger_webhook(self, webhook_path: str, payload: dict | None = None) -> dict:
        self.ctx.authorize("n8n.trigger", webhook_path)
        if not webhook_path.startswith("/"):
            webhook_path = "/" + webhook_path
        self.ctx.log_effect("n8n.trigger", target=webhook_path)
        result = self._request("POST", f"/webhook{webhook_path}", payload or {})
        return {"webhook": webhook_path, "response": result}
