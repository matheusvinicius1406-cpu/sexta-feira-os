"""
Schedule — reminders and timed actions, contract and API tests.

Deterministic (no Ollama, scheduler tick disabled in tests — conftest pins
SCHEDULER_ENABLED=false and tests drive run_due() directly).
"""
import asyncio
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

from app.action.bus import CommandBus
from app.action.service import ActionService
from app.db.database import SessionLocal
from app.models.models import Owner
from app.schedule.service import Scheduler

# ---------- API ----------

def test_schedule_requires_auth(client):
    assert client.get("/api/v1/schedule").status_code == 401


def test_create_list_and_cancel_reminder(client, owner_headers):
    created = client.post(
        "/api/v1/schedule",
        json={"kind": "reminder", "text": "Beber água", "in_minutes": 5},
        headers=owner_headers,
    )
    assert created.status_code == 200
    task = created.json()
    assert task["text"] == "Beber água" and task["kind"] == "reminder"
    assert task["due_at"] and task["status"] in ("pending", "scheduled")

    items = client.get("/api/v1/schedule", headers=owner_headers).json()
    assert any(t["id"] == task["id"] for t in items)

    cancelled = client.delete(f"/api/v1/schedule/{task['id']}", headers=owner_headers)
    assert cancelled.status_code == 200
    assert not any(
        t["id"] == task["id"]
        for t in client.get("/api/v1/schedule", headers=owner_headers).json()
    )


def test_create_timed_action(client, owner_headers):
    created = client.post(
        "/api/v1/schedule",
        json={"kind": "action", "device": "celular", "action": "open_app",
              "params": {"app": "whatsapp"}, "at": _future_iso()},
        headers=owner_headers,
    )
    assert created.status_code == 200
    assert created.json()["kind"] == "action"
    assert created.json()["device"] == "celular"


def test_action_without_action_field_is_400(client, owner_headers):
    r = client.post(
        "/api/v1/schedule",
        json={"kind": "action", "at": _future_iso()},
        headers=owner_headers,
    )
    assert r.status_code == 400


def test_missing_when_is_400(client, owner_headers):
    r = client.post(
        "/api/v1/schedule",
        json={"kind": "reminder", "text": "sem quando"},
        headers=owner_headers,
    )
    assert r.status_code == 400


def test_cancel_unknown_returns_404(client, owner_headers):
    r = client.delete(f"/api/v1/schedule/{uuid.uuid4().hex}", headers=owner_headers)
    assert r.status_code == 404


def test_recurring_reminder(client, owner_headers):
    created = client.post(
        "/api/v1/schedule",
        json={"kind": "reminder", "text": "Alongar", "in_minutes": 1,
              "recurrence_seconds": 3600},
        headers=owner_headers,
    )
    assert created.status_code == 200
    assert created.json()["recurrence_seconds"] == 3600


def test_list_include_done(client, owner_headers):
    created = client.post(
        "/api/v1/schedule", json={"kind": "reminder", "text": "Breve", "in_minutes": 1},
        headers=owner_headers,
    ).json()

    # Drive it to completion the way the kernel's own tick would, then check
    # include_done filtering. run_due is async and only fires tasks whose time
    # has come, so advance the clock past the due date.
    db = SessionLocal()
    scheduler = Scheduler(actions=ActionService(bus=CommandBus()))
    try:
        owner = db.query(Owner).filter(Owner.email == os.environ["OWNER_EMAIL"]).first()
        asyncio.run(
            scheduler.run_due(db, now=datetime.now(UTC) + timedelta(minutes=2))
        )
        done = scheduler.list(db, owner.id, include_done=True)
    finally:
        db.close()
    assert any(t["id"] == created["id"] for t in done)


# ---------- helpers ----------

def _future_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 3600))


# ---------- Service: owner isolation ----------

def test_schedule_is_owner_scoped():
    # Scheduler needs an ActionService (used when firing reminders/actions);
    # a bare CommandBus is enough — nothing is dispatched in this test.
    scheduler = Scheduler(actions=ActionService(bus=CommandBus()))
    a, b = f"o-{uuid.uuid4().hex}", f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        scheduler.schedule(db, a, kind="reminder", due_at=datetime.now(UTC) + timedelta(minutes=1), text="de A")
        scheduler.schedule(db, b, kind="reminder", due_at=datetime.now(UTC) + timedelta(minutes=1), text="de B")
        texts_a = {t["text"] for t in scheduler.list(db, a)}
    finally:
        db.close()
    assert texts_a == {"de A"}
