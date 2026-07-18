"""
Decision Engine — contract and API tests.

Deterministic (no Ollama). They prove scoring is a pure weighted sum, that the
"next goal" decision honors priority, deadline urgency and momentum, adapts to
the owner's inferred energy (World Model), and is persisted + emitted as an event.
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from app.db.database import SessionLocal
from app.decision.service import DecisionEngine
from app.events.bus import EventBus
from app.planning.service import PlanningEngine
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


# ---------- pure scoring primitive ----------

def test_score_options_is_weighted_and_ordered():
    weights = {"priority": 0.5, "urgency": 0.3, "momentum": 0.2}
    options = [
        {"id": "a", "label": "A", "criteria": {"priority": 0.2, "urgency": 0.0, "momentum": 0.0}},
        {"id": "b", "label": "B", "criteria": {"priority": 1.0, "urgency": 0.0, "momentum": 0.0}},
    ]
    ranked = DecisionEngine.score_options(options, weights)
    assert ranked[0]["id"] == "b"
    assert ranked[0]["score"] == 0.5
    assert ranked[1]["score"] == 0.1


def test_score_options_tie_breaks_by_label():
    weights = {"priority": 1.0}
    options = [
        {"id": "2", "label": "Zeta", "criteria": {"priority": 0.5}},
        {"id": "1", "label": "Alfa", "criteria": {"priority": 0.5}},
    ]
    ranked = DecisionEngine.score_options(options, weights)
    assert [o["label"] for o in ranked] == ["Alfa", "Zeta"]  # deterministic tie-break


# ---------- decide_next_goal ----------

def test_priority_dominates_by_default():
    planning = PlanningEngine()
    engine = DecisionEngine(planning=planning)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(planning.create_goal(db, owner, "Baixa", priority=1))
        asyncio.run(planning.create_goal(db, owner, "Alta", priority=5))
        d = asyncio.run(engine.decide_next_goal(db, owner))
        chosen = d.chosen_label
    finally:
        db.close()
    assert chosen == "Alta"


def test_sooner_deadline_wins_at_equal_priority():
    planning = PlanningEngine()
    engine = DecisionEngine(planning=planning)
    owner = f"o-{uuid.uuid4().hex}"
    soon = datetime.now(UTC) + timedelta(days=1)
    far = datetime.now(UTC) + timedelta(days=20)
    db = SessionLocal()
    try:
        asyncio.run(planning.create_goal(db, owner, "Prazo longe", priority=3, due_at=far))
        asyncio.run(planning.create_goal(db, owner, "Prazo perto", priority=3, due_at=soon))
        d = asyncio.run(engine.decide_next_goal(db, owner))
        chosen = d.chosen_label
    finally:
        db.close()
    assert chosen == "Prazo perto"


def test_low_energy_policy_prefers_near_complete():
    planning = PlanningEngine()
    world = WorldModel()
    engine = DecisionEngine(planning=planning, world=world)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        big = asyncio.run(planning.create_goal(db, owner, "Grande e no começo", priority=5))
        asyncio.run(planning.set_progress(db, owner, big.id, 0.1))
        small = asyncio.run(planning.create_goal(db, owner, "Quase pronto", priority=2))
        asyncio.run(planning.set_progress(db, owner, small.id, 0.9))
        # Owner is tired -> the policy should favor finishing the near-complete one.
        world.set_fact(db, owner, "humor", "cansado", category="user_state")
        d = asyncio.run(engine.decide_next_goal(db, owner))
        chosen, policy = d.chosen_label, d.policy
    finally:
        db.close()
    assert policy == "low_energy"
    assert chosen == "Quase pronto"


def test_decision_persisted_event_and_world():
    planning = PlanningEngine()
    world = WorldModel()
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("decisao.tomada", lambda db, ev: seen.append(ev.type))
    engine = DecisionEngine(planning=planning, world=world, events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(planning.create_goal(db, owner, "Única meta", priority=3))
        d = asyncio.run(engine.decide_next_goal(db, owner))
        did = d.id
        in_history = any(h.id == did for h in engine.history(db, owner))
        focus = world.get_fact(db, owner, "foco_decidido")
        focus_val = focus.value if focus else None
    finally:
        db.close()
    assert in_history
    assert seen == ["decisao.tomada"]
    assert focus_val == "Única meta"


def test_no_open_goals_returns_none():
    engine = DecisionEngine(planning=PlanningEngine())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        d = asyncio.run(engine.decide_next_goal(db, owner))
    finally:
        db.close()
    assert d is None


# ---------- API ----------

def test_decision_requires_auth(client):
    assert client.get("/api/v1/decision/history").status_code == 403


def test_decide_next_api_roundtrip(client, owner_headers):
    client.post("/api/v1/planning/goals",
                json={"title": "Meta para decidir", "priority": 5}, headers=owner_headers)
    r = client.post("/api/v1/decision/next", headers=owner_headers).json()
    assert r["decision"] is not None
    dec = r["decision"]
    assert dec["chosen_label"]
    assert dec["rationale"]
    assert isinstance(dec["options"], list) and dec["options"]
    # Audit trail + fetch by id.
    hist = client.get("/api/v1/decision/history", headers=owner_headers).json()
    assert any(h["id"] == dec["id"] for h in hist)
    one = client.get(f"/api/v1/decision/{dec['id']}", headers=owner_headers).json()
    assert one["id"] == dec["id"]
