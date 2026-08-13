"""
Briefing — contract and API tests.

Deterministic (no Ollama). They prove the briefing weaves the five pillars from
LOCAL data, renders a readable summary, persists a history, and that the daily
"morning report" can be scheduled through the existing Scheduler (kind="briefing").
"""
import asyncio
import uuid

from app.briefing.service import BriefingService
from app.db.database import SessionLocal
from app.events.bus import EventBus
from app.planning.service import PlanningEngine
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


# ---------- service ----------

def test_briefing_weaves_pillars_and_persists():
    world = WorldModel()
    planning = PlanningEngine(world=world)
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("briefing.gerado", lambda db, ev: seen.append(ev.type))
    svc = BriefingService(world=world, planning=planning, events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        world.set_fact(db, owner, "localizacao", "casa", category="environment")
        asyncio.run(planning.create_goal(db, owner, "Estudar cálculo", priority=5))
        b = asyncio.run(svc.generate(db, owner))
        summary = b.summary
        found = svc.latest(db, owner) is not None
    finally:
        db.close()
    assert "Estudar cálculo" in summary
    assert "localizacao" in summary
    assert seen == ["briefing.gerado"]
    assert found


def test_briefing_degrades_gracefully_when_empty():
    svc = BriefingService()  # no pillars wired
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        b = asyncio.run(svc.generate(db, owner))
        summary = b.summary
    finally:
        db.close()
    assert "Nada a reportar" in summary


def test_scheduler_fires_briefing_kind():
    """A scheduled task of kind='briefing' generates a briefing when due."""
    from datetime import UTC, datetime, timedelta

    from app.action.service import ActionService
    from app.schedule.service import Scheduler

    class _Bus:
        async def publish(self, *a, **k):
            return None

    class _Actions(ActionService):
        def __init__(self):
            self.dispatched = []

        async def dispatch(self, db, owner_id, device, action, params):
            self.dispatched.append((action, params))
            return {"ok": True, "device": device, "delivered": True}

    world = WorldModel()
    planning = PlanningEngine(world=world)
    briefing = BriefingService(world=world, planning=planning)
    actions = _Actions()
    scheduler = Scheduler(actions, events=_Bus(), briefing=briefing)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(planning.create_goal(db, owner, "Meta do dia"))
        scheduler.schedule(
            db, owner, kind="briefing",
            due_at=datetime.now(UTC) - timedelta(minutes=1),  # already due
        )
        fired = asyncio.run(scheduler.run_due(db))
        latest = briefing.latest(db, owner)
    finally:
        db.close()
    assert fired == 1
    assert latest is not None and latest.kind == "daily"
    assert actions.dispatched and actions.dispatched[0][0] == "notify"


# ---------- API ----------

def test_briefing_requires_auth(client):
    assert client.get("/api/v1/briefing").status_code == 401


def test_briefing_api_generate_and_schedule(client, owner_headers):
    client.post("/api/v1/planning/goals",
                json={"title": "Meta para o briefing", "priority": 4}, headers=owner_headers)
    r = client.post("/api/v1/briefing", headers=owner_headers).json()
    assert "Meta para o briefing" in r["summary"]
    assert isinstance(r["content"], dict)
    latest = client.get("/api/v1/briefing/latest", headers=owner_headers).json()
    assert latest["id"] == r["id"]
    sched = client.post("/api/v1/briefing/schedule", json={"hour": 7}, headers=owner_headers).json()
    assert sched["recurrence_seconds"] == 86400


def test_briefing_includes_the_focus_the_decision_engine_picked(client, owner_headers):
    """"Foco sugerido" must actually reach the briefing.

    It never did. PlanningStep built the BriefingService with
    `decision=kernel.decision` one step BEFORE DecisionStep assigned it, so the
    service held None; `_focus()` returns None for a falsy decision and
    `_render()` omits the line when focus is falsy. Every other section rendered,
    the endpoint answered 200, and one of the briefing's five advertised pillars
    was simply absent — in every kernel ever booted.

    Asserting the rendered text rather than the wiring is deliberate: it fails
    for a re-broken pipeline AND for a briefing that silently stops rendering the
    section for any other reason.
    """
    client.post("/api/v1/planning/goals",
                json={"title": "Meta decisiva do foco", "priority": 5}, headers=owner_headers)
    r = client.post("/api/v1/briefing", headers=owner_headers).json()

    focus = r["content"]["focus"]
    assert focus is not None, "seção 'focus' vazia — o Decision Engine não chegou ao briefing"
    assert focus["goal"], "o foco veio sem meta escolhida"
    assert "Foco sugerido:" in r["summary"], (
        "o texto do briefing não traz a linha 'Foco sugerido' — "
        f"resumo obtido:\n{r['summary']}"
    )
