"""
ConnectorService — the API capability registry + safe execution engine.

The owner defines "capabilities" (one API call each). The brain invokes them BY
NAME; it can never call an arbitrary URL, so prompt injection can't turn into
SSRF. Templates ({param}, {secret:NAME}) are filled at call time — secrets come
from the encrypted vault and never appear in logs or responses.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.connectors.vault import Vault
from app.core.config import settings
from app.models.models import Capability, Secret

logger = logging.getLogger("sexta-feira.connectors")

_TOKEN = re.compile(r"\{(secret:[A-Za-z0-9_\-]+|[A-Za-z0-9_\-]+)\}")


def _now() -> datetime:
    return datetime.now(UTC)


def _render_str(value: str, params: dict, get_secret: Callable[[str], str]) -> str:
    def repl(m: re.Match) -> str:
        tok = m.group(1)
        if tok.startswith("secret:"):
            return get_secret(tok.split(":", 1)[1])
        return str(params.get(tok, ""))
    return _TOKEN.sub(repl, value)


def _render_obj(obj: Any, params: dict, get_secret: Callable[[str], str]) -> Any:
    if isinstance(obj, str):
        m = _TOKEN.fullmatch(obj)
        if m and not m.group(1).startswith("secret:") and m.group(1) in params:
            return params[m.group(1)]          # keep the param's native type
        return _render_str(obj, params, get_secret)
    if isinstance(obj, dict):
        return {k: _render_obj(v, params, get_secret) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_render_obj(v, params, get_secret) for v in obj]
    return obj


class ConnectorService:
    def __init__(self, vault: Vault):
        self.vault = vault
        self._client = httpx.AsyncClient()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------- capabilities CRUD ----------

    def get(self, db: Session, owner_id: str, name: str) -> Capability | None:
        return db.query(Capability).filter(
            Capability.owner_id == owner_id, Capability.name == name
        ).first()

    def upsert_capability(self, db: Session, owner_id: str, spec: dict) -> Capability:
        cap = self.get(db, owner_id, spec["name"])
        fields = dict(
            description=spec.get("description", ""),
            category=spec.get("category", "general"),
            method=spec.get("method", "GET").upper(),
            url=spec["url"],
            query=json.dumps(spec["query"]) if spec.get("query") else None,
            headers=json.dumps(spec["headers"]) if spec.get("headers") else None,
            body=json.dumps(spec["body"]) if spec.get("body") is not None else None,
            params_schema=json.dumps(spec["params_schema"]) if spec.get("params_schema") else None,
            enabled=spec.get("enabled", True),
        )
        if cap:
            for k, v in fields.items():
                setattr(cap, k, v)
        else:
            cap = Capability(id=str(uuid.uuid4()), owner_id=owner_id, name=spec["name"], **fields)
            db.add(cap)
        db.commit()
        db.refresh(cap)
        return cap

    def list_capabilities(self, db: Session, owner_id: str, query: str | None = None) -> list[dict]:
        caps = db.query(Capability).filter(Capability.owner_id == owner_id).all()
        q = (query or "").strip().lower()
        out = []
        for c in caps:
            if q and q not in c.name.lower() and q not in (c.description or "").lower() \
                    and q not in (c.category or "").lower():
                continue
            out.append({
                "name": c.name, "description": c.description, "category": c.category,
                "method": c.method, "enabled": c.enabled,
                "params": json.loads(c.params_schema) if c.params_schema else [],
            })
        return out

    def delete_capability(self, db: Session, owner_id: str, name: str) -> bool:
        cap = self.get(db, owner_id, name)
        if not cap:
            return False
        db.delete(cap)
        db.commit()
        return True

    # ---------- secrets ----------

    def set_secret(self, db: Session, owner_id: str, name: str, value: str) -> None:
        enc = self.vault.encrypt(value)
        existing = db.query(Secret).filter(
            Secret.owner_id == owner_id, Secret.name == name
        ).first()
        if existing:
            existing.value_encrypted = enc
        else:
            db.add(Secret(id=str(uuid.uuid4()), owner_id=owner_id, name=name, value_encrypted=enc))
        db.commit()

    def get_secret_value(self, db: Session, owner_id: str, name: str) -> str | None:
        # Honeytoken tripwire: a secret named honeypot.* is bait, never a real
        # credential. Reading one means someone is probing the vault — record
        # the threat, return nothing, leak nothing.
        from app.core.threats import is_honeypot, record_threat_sync

        if is_honeypot(name):
            record_threat_sync(
                db, "honeypot",
                f"honeytoken '{name}' tocado no cofre de segredos",
            )
            return None
        s = db.query(Secret).filter(Secret.owner_id == owner_id, Secret.name == name).first()
        return self.vault.decrypt(s.value_encrypted) if s else None

    def list_secret_names(self, db: Session, owner_id: str) -> list[str]:
        return [s.name for s in db.query(Secret).filter(Secret.owner_id == owner_id).all()]

    def delete_secret(self, db: Session, owner_id: str, name: str) -> bool:
        s = db.query(Secret).filter(Secret.owner_id == owner_id, Secret.name == name).first()
        if not s:
            return False
        db.delete(s)
        db.commit()
        return True

    # ---------- invoke ----------

    async def invoke(self, db: Session, owner_id: str, name: str, params: dict | None) -> dict:
        cap = self.get(db, owner_id, name)
        if not cap:
            return {"ok": False, "error": f"Capacidade '{name}' não existe."}
        if not cap.enabled:
            return {"ok": False, "error": f"Capacidade '{name}' está desativada."}
        params = params or {}

        cache: dict[str, str] = {}

        def get_secret(sname: str) -> str:
            if sname not in cache:
                cache[sname] = self.get_secret_value(db, owner_id, sname) or ""
            return cache[sname]

        url = _render_str(cap.url, params, get_secret)
        query = _render_obj(json.loads(cap.query), params, get_secret) if cap.query else None
        headers = _render_obj(json.loads(cap.headers), params, get_secret) if cap.headers else None
        body = _render_obj(json.loads(cap.body), params, get_secret) if cap.body else None

        try:
            resp = await self._client.request(
                cap.method.upper(), url, params=query, headers=headers,
                json=body if body is not None else None,
                timeout=settings.connectors_timeout_seconds,
            )
        except httpx.RequestError as e:
            return {"ok": False, "error": f"Falha de rede: {e}"}

        raw = resp.content[: settings.connectors_max_response_kb * 1024]
        try:
            data: Any = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = raw.decode("utf-8", "replace")
        return {"ok": resp.is_success, "status": resp.status_code, "data": data}
