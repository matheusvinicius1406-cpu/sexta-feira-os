"""
Journal + Habits, Time Tracker and Eval Harness — contract and API tests.

Deterministic (no Ollama; injectable clock and fake brains). They prove entries
persist and distil, habit check-ins are idempotent with exact streaks reflected
in the World Model, one timer runs at a time with exact durations, and evals
score the local brain and feed the Learning Engine.
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from app.db.database import SessionLocal
from app.evals.service import EvalHarness
from app.events.bus import EventBus
from app.journal.service import HabitService, JournalService
from app.learning.service import LearningEngine
from app.timetrack.service import TimeTracker
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


# ---------- journal ----------

def test_journal_persists_emits_and_distils():
    class _SpyExtractor:
        def __init__(self):
            self.calls = []

        async def extract(self, db, owner_id, user_text, reply):
            self.calls.append(user_text)
            return 1

    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("diario.registrado", lambda db, ev: seen.append(ev.type))
    spy = _SpyExtractor()
    svc = JournalService(events=bus, extractor=spy)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(svc.add(db, owner, "Hoje estudei grafos e rendeu muito", mood="animado"))
        entries = svc.list(db, owner)
    finally:
        db.close()
    assert len(entries) == 1 and entries[0].mood == "animado"
    assert seen == ["diario.registrado"]
    assert spy.calls == ["Hoje estudei grafos e rendeu muito"]  # distillation ran


def test_journal_survives_broken_extractor():
    class _Boom:
        async def extract(self, *a, **k):
            raise RuntimeError("kaboom")

    svc = JournalService(extractor=_Boom())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        entry = asyncio.run(svc.add(db, owner, "nota que não pode se perder"))
        content = entry.content
    finally:
        db.close()
    assert content == "nota que não pode se perder"


# ---------- habits ----------

def test_habit_check_idempotent_streak_and_world():
    world = WorldModel()
    bus = EventBus()
    seen: list[dict] = []
    bus.subscribe("habito.marcado", lambda db, ev: seen.append(EventBus.decode_payload(ev)))
    svc = HabitService(world=world, events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    today = datetime.now(UTC)
    d = lambda offset: (today - timedelta(days=offset)).strftime("%Y-%m-%d")  # noqa: E731
    db = SessionLocal()
    try:
        asyncio.run(svc.check(db, owner, "Academia", day=d(2)))
        asyncio.run(svc.check(db, owner, "academia", day=d(1)))   # same habit (slug)
        out = asyncio.run(svc.check(db, owner, "ACADEMIA", day=d(0)))
        again = asyncio.run(svc.check(db, owner, "academia", day=d(0)))  # idempotent
        fact = world.get_fact(db, owner, "habito:academia")
        listed = svc.list(db, owner)
    finally:
        db.close()
    assert out["streak"] == 3
    assert again["already"] is True
    assert len(seen) == 3                       # no event for the duplicate check
    assert fact and "3 dias" in fact.value      # the present knows the streak
    assert listed == [{"id": listed[0]["id"], "name": "academia",
                       "schedule": "daily", "streak": 3}]


def test_habit_streak_breaks_on_gap():
    svc = HabitService()
    owner = f"o-{uuid.uuid4().hex}"
    today = datetime.now(UTC)
    d = lambda offset: (today - timedelta(days=offset)).strftime("%Y-%m-%d")  # noqa: E731
    db = SessionLocal()
    try:
        asyncio.run(svc.check(db, owner, "leitura", day=d(3)))    # gap at d(2)... d(1)
        asyncio.run(svc.check(db, owner, "leitura", day=d(0)))
        streak = svc.streak(db, owner, "leitura")
    finally:
        db.close()
    assert streak == 1                          # only today counts after the gap


# ---------- time tracker ----------

def test_single_timer_exact_durations_and_world():
    clock = {"now": datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)}
    world = WorldModel()
    tracker = TimeTracker(world=world, now=lambda: clock["now"])
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(tracker.start(db, owner, "estudo"))
        assert world.get_fact(db, owner, "atividade_atual").value == "estudo"
        clock["now"] += timedelta(minutes=30)
        asyncio.run(tracker.start(db, owner, "código"))   # closes "estudo" at 30min
        clock["now"] += timedelta(minutes=15)
        out = asyncio.run(tracker.stop(db, owner))
        summary = {s["label"]: s["seconds"] for s in tracker.summary(db, owner)}
        cleared = world.get_fact(db, owner, "atividade_atual")
        current = tracker.current(db, owner)
    finally:
        db.close()
    assert out == {"label": "código", "seconds": 900}
    assert summary == {"estudo": 1800, "código": 900}
    assert cleared is None                      # the present forgot the activity
    assert current is None                      # nothing left running


def test_stop_without_timer_is_noop():
    tracker = TimeTracker()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        out = asyncio.run(tracker.stop(db, owner))
    finally:
        db.close()
    assert out is None


# ---------- evals ----------

class _FakeBrain:
    """Replies 'Paris.' to capital questions, gibberish otherwise."""

    async def chat(self, messages, temperature=0.0, max_tokens=300):
        text = messages[-1]["content"].lower()
        return "A capital é Paris." if "capital" in text else "não sei"


def test_evals_score_persist_and_feed_learning():
    bus = EventBus()
    seen: list[dict] = []
    bus.subscribe("avaliacao.executada", lambda db, ev: seen.append(EventBus.decode_payload(ev)))
    learning = LearningEngine()
    harness = EvalHarness(_FakeBrain(), events=bus, learning=learning)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        harness.add_case(db, owner, "capital", "Qual a capital da França?", "paris")
        harness.add_case(db, owner, "impossivel", "Quanto é 2+2?", "quatro")
        run = asyncio.run(harness.run(db, owner))
        score, passed, total = run.score, run.passed, run.total
        lessons = learning.lessons(db, owner, tag="eval")
        history = harness.history(db, owner)
    finally:
        db.close()
    assert (passed, total, score) == (1, 2, 0.5)
    assert seen == [{"score": 0.5, "passed": 1, "total": 2}]
    assert lessons and lessons[0].quality == 0.5       # the score became a lesson
    assert len(history) == 1


def test_evals_run_without_cases_returns_none():
    harness = EvalHarness(_FakeBrain())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        assert asyncio.run(harness.run(db, owner)) is None
    finally:
        db.close()


# ---------- API ----------

def test_life_apis_require_auth(client):
    assert client.get("/api/v1/journal").status_code == 403
    assert client.get("/api/v1/habits").status_code == 403
    assert client.get("/api/v1/time/summary").status_code == 403
    assert client.get("/api/v1/evals/cases").status_code == 403


def test_life_api_roundtrip(client, owner_headers):
    # journal (kernel extractor hits the offline brain — entry must survive)
    r = client.post("/api/v1/journal", json={"content": "primeiro registro do diário"},
                    headers=owner_headers)
    assert r.status_code == 200
    assert any("primeiro registro" in e["content"]
               for e in client.get("/api/v1/journal", headers=owner_headers).json())
    # habits
    out = client.post("/api/v1/habits/check", json={"name": "meditar"},
                      headers=owner_headers).json()
    assert out["streak"] == 1
    # time
    client.post("/api/v1/time/start", json={"label": "planejamento"}, headers=owner_headers)
    assert client.get("/api/v1/time/current",
                      headers=owner_headers).json()["running"]["label"] == "planejamento"
    stopped = client.post("/api/v1/time/stop", headers=owner_headers).json()
    assert stopped["label"] == "planejamento"
    # evals: cases persist; run degrades to 503 with the brain offline
    client.post("/api/v1/evals/cases", headers=owner_headers,
                json={"name": "sanidade", "prompt": "diga oi", "expected_contains": "oi"})
    assert len(client.get("/api/v1/evals/cases", headers=owner_headers).json()) == 1
    assert client.post("/api/v1/evals/run", headers=owner_headers).status_code == 503
