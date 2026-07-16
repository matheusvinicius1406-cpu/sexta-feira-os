"""
n8n bridge — the kernel's hands.

n8n is a self-hosted workflow engine (hundreds of integrations => thousands of
possible automations). It runs on YOUR machine. Sexta-Feira uses it to ACT:

  * list workflows            -> n8n Public API   (GET /api/v1/workflows)
  * trigger a workflow        -> its Webhook node  (POST {endpoint}/webhook/{path})

If n8n is unreachable, methods raise AutomationUnavailable so the API returns a
clean 503 — same graceful pattern as the brain and voice.

Privacy note: the ENGINE is local. A given workflow may of course reach out to a
third party (that's what "send an email" means) — that's your choice per flow,
not a leak of the brain's private data.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("sexta-feira.automation")


class AutomationUnavailable(RuntimeError):
    """Raised when the local n8n instance can't be reached."""


class N8nClient:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self.endpoint = (endpoint or settings.n8n_endpoint).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.n8n_api_key
        self._client = httpx.AsyncClient(base_url=self.endpoint, timeout=httpx.Timeout(30.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    def _api_headers(self) -> dict[str, str]:
        return {"X-N8N-API-KEY": self.api_key} if self.api_key else {}

    async def health(self) -> bool:
        try:
            r = await self._client.get("/healthz", timeout=5.0)
            return r.status_code == 200
        except Exception as e:  # noqa: BLE001
            logger.debug("n8n health failed: %s", e)
            return False

    async def list_workflows(self) -> list[dict[str, Any]]:
        """List workflows via the n8n Public API (needs N8N_API_KEY)."""
        if not self.api_key:
            raise AutomationUnavailable(
                "N8N_API_KEY não configurada. Crie uma chave no n8n "
                "(Settings → API) e coloque em N8N_API_KEY no .env."
            )
        try:
            r = await self._client.get("/api/v1/workflows", headers=self._api_headers())
            r.raise_for_status()
            data = r.json().get("data", [])
            return [
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "active": w.get("active", False),
                    "tags": [t.get("name") for t in w.get("tags", [])],
                }
                for w in data
            ]
        except httpx.ConnectError as e:
            raise AutomationUnavailable(
                f"n8n não respondeu em {self.endpoint}. Suba o n8n (docker compose up n8n)."
            ) from e

    async def trigger(self, webhook_path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fire a workflow by its Webhook node path."""
        path = webhook_path.strip("/")
        try:
            r = await self._client.post(
                f"/{settings.n8n_webhook_prefix}/{path}", json=payload or {}
            )
            r.raise_for_status()
            # n8n webhooks may return JSON or empty; be tolerant.
            try:
                body = r.json()
            except Exception:  # noqa: BLE001
                body = {"raw": r.text}
            return {"ok": True, "status_code": r.status_code, "result": body}
        except httpx.ConnectError as e:
            raise AutomationUnavailable(
                f"n8n não respondeu em {self.endpoint}. Suba o n8n (docker compose up n8n)."
            ) from e
        except httpx.HTTPStatusError as e:
            return {"ok": False, "status_code": e.response.status_code, "error": e.response.text}

    async def status(self) -> dict[str, Any]:
        return {
            "enabled": settings.automations_enabled,
            "endpoint": self.endpoint,
            "online": await self.health(),
            "api_key_set": bool(self.api_key),
        }
