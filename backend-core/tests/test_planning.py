"""
Planning Engine — contract and API tests.

Deterministic (no Ollama). They prove goals are created/listed by priority,
decomposed into subtasks with progress roll-up, blocked by dependencies and
unblocked (with a 'tarefa.desbloqueada' event) on completion, and that the
current focus is reflected in the World Model.
"""
import asyncio
import uuid

from app.db.database import SessionLocal
from app.events.bus import EventBus
from app.planning.service import PlanningEngine
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


# ---------- API ----------

def test_planning_requires_auth(client):
    assert client.get("/api/v1/planning/goals").status_code == 403


def test_create_list_and_priority_order(client, owner_headers):
    lo = client.post("/api/v1/planning/goals",
                     json={"title": "Objetivo baixo", "priority": 1}, headers=owner_headers).json()
    hi = client.post("/api/v1/planning/goals",
                     json={"title": "Objetivo alto", "priority": 5}, headers=owner_headers).json()
    goals = client.get("/api/v1/planning/goals", headers=owner_headers).json()
    ids = [g["id"] for g in goals]
    assert ids.index(hi["id"]) < ids.index(lo["id"])  # higher priority first


def test_decompose_and_progress_rollup(client, owner_headers):
    parent = client.post("/api/v1/planning/goals",
                         json={"title": "Grande objetivo"}, headers=owner_headers).json()
    subs = client.post(f"/api/v1/planning/goals/{parent['id']}/subtasks",
                       json={"subtasks": ["parte A", "parte B"]}, headers=owner_headers).json()
    assert len(subs) == 2
    # Complete one child → parent progress is the mean (0.5).
    client.post(f"/api/v1/planning/goals/{subs[0]['id']}/progress",
                json={"progress": 1.0}, headers=owner_headers)
    detail = client.get(f"/api/v1/planning/goals/{parent['id']}", headers=owner_headers).json()
    assert detail["progress"] == 0.5
    assert len(detail["subtasks"]) == 2


def test_complete_via_api_sets_done(client, owner_headers):
    g = client.post("/api/v1/planning/goals",
                    json={"title": "Concluir isto"}, headers=owner_headers).json()
    done = client.post(f"/api/v1/planning/goals/{g['id']}/complete", headers=owner_headers).json()
    assert done["status"] == "done"
    assert done["progress"] == 1.0


def test_goal_reflected_in_world_model(client, owner_headers):
    client.post("/api/v1/planning/goals",
                json={"title": "Estudar cálculo", "priority": 5}, headers=owner_headers)
    world = client.get("/api/v1/world", headers=owner_headers).json()
    assert any(f["key"] == "objetivos_ativos" for f in world)
    assert any(f["key"] == "objetivo_atual" for f in world)


# ---------- Service: dependencies, unblock event, isolation ----------

def test_dependency_blocks_and_unblocks_with_event():
    bus = EventBus()
    unblocked: list[str] = []
    bus.subscribe("tarefa.desbloqueada", lambda db, ev: unblocked.append(ev.type))
    planning = PlanningEngine(world=None, events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        a = asyncio.run(planning.create_goal(db, owner, "Pré-requisito"))
        b = asyncio.run(planning.create_goal(db, owner, "Depende de A"))
        planning.add_dependency(db, owner, b.id, a.id)
        blocked_status = planning.get_goal(db, owner, b.id).status
        asyncio.run(planning.complete(db, owner, a.id))
        after_status = planning.get_goal(db, owner, b.id).status
    finally:
        db.close()
    assert blocked_status == "blocked"
    assert after_status in ("pending", "active")
    assert unblocked == ["tarefa.desbloqueada"]


def test_complete_emits_event():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("objetivo.*", lambda db, ev: seen.append(ev.type))
    planning = PlanningEngine(world=None, events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        g = asyncio.run(planning.create_goal(db, owner, "Meta"))
        asyncio.run(planning.set_progress(db, owner, g.id, 1.0))
    finally:
        db.close()
    assert "objetivo.criado" in seen
    assert "objetivo.concluido" in seen


def test_world_focus_updates():
    world = WorldModel()
    planning = PlanningEngine(world=world, events=None)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(planning.create_goal(db, owner, "Foco principal", priority=5))
        fact = world.get_fact(db, owner, "objetivo_atual")
        val = fact.value if fact else None
    finally:
        db.close()
    assert val == "Foco principal"


def test_planning_is_owner_scoped():
    planning = PlanningEngine()
    a, b = f"o-{uuid.uuid4().hex}", f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(planning.create_goal(db, a, "meta de A"))
        asyncio.run(planning.create_goal(db, b, "meta de B"))
        titles_a = {g.title for g in planning.list_goals(db, a)}
        only_a = all(g.owner_id == a for g in planning.list_goals(db, a))
    finally:
        db.close()
    assert titles_a == {"meta de A"}
    assert only_a is True
