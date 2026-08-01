"""
HTTP node — reaching anything that speaks HTTP.

Secrets belong in headers via `{{ secret.NOME }}`: the vault resolves them at
call time, they never live in the workflow's JSON, and the engine scrubs them out
of the persisted node output.
"""
from __future__ import annotations

import json
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata
from app.core.config import settings


class _HttpConfig(BaseModel):
    url: str = Field(..., min_length=1)
    metodo: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"] = "GET"
    cabecalhos: dict[str, str] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)
    corpo: Any = None
    formato: Literal["json", "texto"] = "json"
    # False turns a 4xx/5xx into a normal item (`ok: false`) instead of a failure,
    # which is what you want when the next node is supposed to react to it.
    falhar_em_erro: bool = True
    timeout_segundos: float = Field(default=0.0, ge=0.0, le=300.0)


class HttpRequestNode(Node):
    """One HTTP request. Emits `{ok, status, dados, cabecalhos}`."""

    metadata = NodeMetadata(
        type="http", name="Requisição HTTP", category="rede",
        description="Chama uma URL (GET/POST/...) e emite a resposta.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _HttpConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        cfg = self.config
        timeout = cfg.timeout_segundos or settings.teia_http_timeout_seconds

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                response = await client.request(
                    cfg.metodo,
                    cfg.url,
                    headers=cfg.cabecalhos or None,
                    params=cfg.query or None,
                    json=cfg.corpo if cfg.corpo is not None else None,
                )
            except httpx.RequestError as e:
                raise RuntimeError(f"falha de rede em {cfg.metodo} {cfg.url}: {e}") from e

        raw = response.content[: settings.teia_http_max_response_kb * 1024]
        if cfg.formato == "json":
            try:
                data: Any = json.loads(raw) if raw else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                data = raw.decode("utf-8", "replace")
        else:
            data = raw.decode("utf-8", "replace")

        if not response.is_success and cfg.falhar_em_erro:
            raise RuntimeError(
                f"{cfg.metodo} {cfg.url} respondeu {response.status_code}: "
                f"{str(data)[:300]}"
            )

        context.log(f"http {cfg.metodo} {cfg.url} → {response.status_code}")
        return NodeOutput.single({
            "ok": response.is_success,
            "status": response.status_code,
            "dados": data,
            "cabecalhos": dict(response.headers),
        })


HTTP_NODES = [HttpRequestNode]
