"""
Cortex · ciclo autônomo — o kernel acorda sozinho a cada hora e o núcleo
avalia as regras: cada regra disparada vira proposta do agente, sem LLM.

  * Scheduler: kind="cortex" dispara o proposer injetado pelo kernel.
  * API: POST /cortex/ciclo/agendar (idempotente) + GET /cortex/ciclo.
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from app.action.bus import CommandBus
from app.action.service import ActionService
from app.db.database import SessionLocal
from app.schedule.service import Scheduler

# ---------- Service: kind="cortex" fires the proposer ----------

def test_cortex_kind_fires_proposer_and_advances_recurrence():
    calls = []

    async def fake_proposer(db, owner_id):
        calls.append(owner_id)

    scheduler = Scheduler(
        actions=ActionService(bus=CommandBus()), cortex_proposer=fake_proposer,
    )
    a = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        scheduler.schedule(
            db, a, kind="cortex",
            due_at=datetime.now(UTC) - timedelta(minutes=5),
            text="Ciclo decisório", recurrence_seconds=3600,
        )
        fired = asyncio.run(scheduler.run_due(db))
        assert fired == 1
        assert calls == [a]
        # Recurring: the task stays pending and advances past the missed cycles.
        tasks = scheduler.list(db, a)
        assert len(tasks) == 1
        assert tasks[0]["status"] == "pending"
        assert tasks[0]["due_at"] > datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    finally:
        db.close()


def test_cortex_kind_without_proposer_skips_honestly():
    scheduler = Scheduler(actions=ActionService(bus=CommandBus()))  # no proposer
    a = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        scheduler.schedule(
            db, a, kind="cortex", due_at=datetime.now(UTC) - timedelta(minutes=1),
            text="sem proposer",
        )
        fired = asyncio.run(scheduler.run_due(db))
        # Fired count still counts it (the tick happened); no crash, no action.
        assert fired == 1
        done = scheduler.list(db, a, include_done=True)
        assert done[0]["status"] == "fired"
    finally:
        db.close()


# ---------- API ----------

def test_ciclo_requires_auth(client):
    assert client.post("/api/v1/cortex/ciclo/agendar", json={}).status_code == 401
    assert client.get("/api/v1/cortex/ciclo").status_code == 401


def test_ciclo_agendar_idempotente(client, owner_headers):
    first = client.post(
        "/api/v1/cortex/ciclo/agendar",
        json={"intervalo_minutos": 60, "iniciar_em_minutos": 1},
        headers=owner_headers,
    )
    assert first.status_code == 200
    task = first.json()
    assert task["repetido"] is False
    assert task["agendado"]["kind"] == "cortex"
    assert task["agendado"]["recurrence_seconds"] == 3600
    assert task["agendado"]["status"] == "pending"

    second = client.post(
        "/api/v1/cortex/ciclo/agendar",
        json={"intervalo_minutos": 60, "iniciar_em_minutos": 1},
        headers=owner_headers,
    )
    assert second.json()["repetido"] is True
    assert second.json()["agendado"]["id"] == task["agendado"]["id"]

    # A different interval is a different schedule (not deduped).
    other = client.post(
        "/api/v1/cortex/ciclo/agendar",
        json={"intervalo_minutos": 30, "iniciar_em_minutos": 1},
        headers=owner_headers,
    )
    assert other.json()["repetido"] is False


def test_ciclo_status_mostra_agendado(client, owner_headers):
    client.post(
        "/api/v1/cortex/ciclo/agendar",
        json={"intervalo_minutos": 60},
        headers=owner_headers,
    )
    status = client.get("/api/v1/cortex/ciclo", headers=owner_headers).json()
    assert status["agendado"]["kind"] == "cortex"
    assert status["engine"] == "symbolic"
    assert isinstance(status["historico"], list)
    assert isinstance(status["propostas"], list)
