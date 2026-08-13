"""
Cognitive Pulse — the kernel's own initiative. Contract and API tests.

Deterministic (no Ollama): a scripted fake brain drives the judgment. They prove
the cycle executes safe tools on its own, files world-changing actions as
PENDING PROPOSALS (never runs them without approval), skips unknown tools and
repeats, notices due goals deterministically, keeps a diary, and that the
confirmation gate (approve/reject) drives the SAME toolkit dispatch path.
"""
import asyncio
import json
import uuid

from app.agent.pulse import CognitivePulse
from app.db.database import SessionLocal
from app.events.bus import EventBus
from app.planning.service import PlanningEngine

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


class _FakeBrain:
    """Scripted LocalBrain: `chat` returns the scripted judgment raw text."""

    def __init__(self, judgment: str = '{"nothing": true}'):
        self.judgment = judgment
        self.calls = 0

    async def chat(self, messages, temperature=0.2, max_tokens=250, **kwargs):
        self.calls += 1
        return self.judgment


class _FakeBrainDown(_FakeBrain):
    async def chat(self, messages, temperature=0.2, max_tokens=250, **kwargs):
        raise RuntimeError("Ollama offline (stub de teste)")


class _SpyToolkit:
    """ToolKit stand-in: records dispatches, returns a canned tool result."""

    def __init__(self):
        self.dispatched: list[tuple[str, dict]] = []

    async def dispatch(self, name, args, db, owner_id):
        self.dispatched.append((name, args))
        return f"resultado de {name}"


def _pulse(brain=None, toolkit=None, events=None, planning=None, journal=None) -> CognitivePulse:
    return CognitivePulse(
        brain or _FakeBrain(), toolkit or _SpyToolkit(),
        world=None, planning=planning, decision=None, learning=None,
        events=events, journal=journal,
    )


# ---------- the cycle: act or propose ----------

def test_tick_executes_safe_tool_on_its_own():
    brain = _FakeBrain(
        json.dumps({"tool": "daily_briefing", "args": {}, "title": "resumo do dia",
                    "reason": "estado mudou"})
    )
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=brain, toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        report = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert toolkit.dispatched == [("daily_briefing", {})]
    assert report["executed"] and report["executed"][0]["tool"] == "daily_briefing"
    assert report["proposed"] == []
    assert brain.calls == 1


def test_tick_world_tool_becomes_pending_proposal_not_executed():
    brain = _FakeBrain(
        json.dumps({"tool": "create_goal", "args": {"title": "organizar o quarto"},
                    "title": "criar objetivo", "reason": "meta antiga"})
    )
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=brain, toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        report = asyncio.run(pulse.tick(db, owner))
        pending = pulse.list_proposals(db, owner, status="pending")
    finally:
        db.close()
    assert toolkit.dispatched == []                     # never ran without approval
    assert report["proposed"] and report["proposed"][0]["tool"] == "create_goal"
    assert len(pending) == 1
    assert pending[0].status == "pending"


def test_tick_nothing_does_nothing():
    pulse = _pulse()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        report = asyncio.run(pulse.tick(db, owner))
        pending = pulse.list_proposals(db, owner, status="pending")
    finally:
        db.close()
    assert report["executed"] == []
    assert report["proposed"] == []
    assert pending == []


def test_tick_skips_unknown_tool():
    brain = _FakeBrain(
        json.dumps({"tool": "faz_tudo", "args": {}, "title": "hack", "reason": "x"})
    )
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=brain, toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        report = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert toolkit.dispatched == []
    assert any("fora da lista" in s for s in report["skipped"])


def test_tick_parses_judgment_wrapped_in_prose():
    brain = _FakeBrain(
        "Aqui vai minha resposta:\n```json\n"
        '{"tool": "recall", "args": {"query": "projeto x"}}\n```'
    )
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=brain, toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        report = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert toolkit.dispatched == [("recall", {"query": "projeto x"})]
    assert report["executed"][0]["tool"] == "recall"


def test_tick_cooldown_stops_repeating_the_same_safe_action():
    brain = _FakeBrain(
        json.dumps({"tool": "decide_next", "args": {}, "title": "foco", "reason": "x"})
    )
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=brain, toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        first = asyncio.run(pulse.tick(db, owner))
        second = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert len(toolkit.dispatched) == 1                 # ran once, then cooldown
    assert len(first["executed"]) == 1
    assert second["executed"] == []
    assert any("já feito há pouco" in s for s in second["skipped"])


def test_tick_degrades_with_brain_offline():
    pulse = _pulse(brain=_FakeBrainDown(), toolkit=_SpyToolkit())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        report = asyncio.run(pulse.tick(db, owner))     # must not raise
    finally:
        db.close()
    assert any("julgamento indisponível" in s for s in report["skipped"])
    assert report["executed"] == []
    assert report["proposed"] == []


def test_tick_duplicate_world_proposal_is_deduplicated():
    judgment = json.dumps({"tool": "schedule_reminder",
                           "args": {"text": "beber água", "in_hours": 2},
                           "title": "lembrete", "reason": "rotina"})
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=_FakeBrain(judgment), toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        first = asyncio.run(pulse.tick(db, owner))
        second = asyncio.run(pulse.tick(db, owner))
        pending = pulse.list_proposals(db, owner, status="pending")
    finally:
        db.close()
    assert toolkit.dispatched == []
    assert len(first["proposed"]) == 1
    assert len(pending) == 1                             # one proposal, not two
    assert any("já proposto" in s for s in second["skipped"])


# ---------- judgment gated on a changed digest (Step 6) ----------


def test_repeated_nothing_on_unchanged_state_judges_only_once():
    """An idle owner (no goals, no world change) should not pay for the same
    'nada a fazer' answer on every tick — see agent_pulse_judge_when_idle."""
    brain = _FakeBrain()  # default: '{"nothing": true}'
    pulse = _pulse(brain=brain, toolkit=_SpyToolkit())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
        second = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert brain.calls == 1
    assert any("julgamento pulado" in s for s in second["skipped"])


def test_a_changed_world_state_is_judged_again():
    """The gate must not silence a genuinely new situation."""
    from app.world.service import WorldModel

    world = WorldModel()
    brain = _FakeBrain()
    pulse = CognitivePulse(brain, _SpyToolkit(), world=world)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
        world.set_fact(db, owner, "localizacao", "aeroporto", category="user_state")
        second = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert brain.calls == 2
    assert not any("julgamento pulado" in s for s in second["skipped"])


def test_judge_when_idle_true_restores_always_judge(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "agent_pulse_judge_when_idle", True)
    brain = _FakeBrain()
    pulse = _pulse(brain=brain, toolkit=_SpyToolkit())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
        asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert brain.calls == 2


def test_an_actionable_judgment_is_reconsidered_next_tick_even_if_unchanged():
    """Only a settled 'nothing' is remembered — a tick that acted must not
    suppress the NEXT tick's judgment just because the digest text matches
    (e.g. a proposal that hasn't changed the pending count yet)."""
    judgment = json.dumps({"tool": "decide_next", "args": {}, "title": "foco", "reason": "x"})
    brain = _FakeBrain(judgment)
    pulse = _pulse(brain=brain, toolkit=_SpyToolkit())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
        asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert brain.calls == 2


def test_a_malformed_judgment_is_retried_not_remembered_as_nothing():
    """A parse failure is 'the model answered badly', not 'there is nothing
    to do' — treating it as settled would permanently silence a brain that
    is malfunctioning on this exact digest."""
    brain = _FakeBrain("isso não é JSON nenhum")
    pulse = _pulse(brain=brain, toolkit=_SpyToolkit())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
        asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert brain.calls == 2


# ---------- deterministic scan + diary ----------

def test_tick_notices_due_goal_without_brain():
    planning = PlanningEngine()
    pulse = _pulse(brain=_FakeBrain(), toolkit=_SpyToolkit(), planning=planning)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        from datetime import UTC, datetime, timedelta
        asyncio.run(planning.create_goal(
            db, owner, "entregar relatório",
            due_at=datetime.now(UTC) + timedelta(hours=12),
        ))
        report = asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert report["noticed"], "the pulse should notice the due goal"
    assert any("relatório" in n for n in report["noticed"])
    assert report["executed"] == []                      # "nothing" judgment


def test_tick_writes_diary_entry_when_something_happened():
    from app.journal.service import JournalService
    from app.models.models import JournalEntry

    journal = JournalService()
    pulse = _pulse(brain=_FakeBrain(
        json.dumps({"tool": "decide_next", "args": {}, "title": "foco", "reason": "x"})
    ), toolkit=_SpyToolkit(), journal=journal)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
        entries = db.query(JournalEntry).filter(JournalEntry.owner_id == owner).all()
    finally:
        db.close()
    assert entries, "the kernel should keep a diary of what the agent did"
    assert any("Pulse" in e.content for e in entries)


def test_pulse_diary_does_not_distil_the_agents_own_log_line():
    """The diary line is what the AGENT did, not a fact about the owner —
    extracting from it anyway was the second, uncosted cascade behind a
    'cheap' pulse tick (journal.add(..., distil=False), Step 6)."""
    from app.journal.service import JournalService

    class _SpyExtractor:
        def __init__(self):
            self.calls = 0

        async def extract(self, db, owner_id, user_text, reply):
            self.calls += 1
            return 0

    extractor = _SpyExtractor()
    journal = JournalService(extractor=extractor)
    pulse = _pulse(brain=_FakeBrain(
        json.dumps({"tool": "decide_next", "args": {}, "title": "foco", "reason": "x"})
    ), toolkit=_SpyToolkit(), journal=journal)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert extractor.calls == 0


def test_tick_publishes_cycle_event():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("pulse.ciclo", lambda db, ev: seen.append(ev.type))
    pulse = _pulse(brain=_FakeBrain(
        json.dumps({"tool": "decide_next", "args": {}, "title": "foco", "reason": "x"})
    ), toolkit=_SpyToolkit(), events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(pulse.tick(db, owner))
    finally:
        db.close()
    assert seen == ["pulse.ciclo"]


# ---------- the confirmation gate ----------

def test_execute_proposal_runs_tool_and_marks_executed():
    toolkit = _SpyToolkit()
    pulse = _pulse(brain=_FakeBrain(), toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        p = pulse.propose(db, owner, "recall", {"query": "x"}, "lembrar", "porque sim")
        done = asyncio.run(pulse.execute_proposal(db, owner, p.id))
        status, result = done.status, done.result
    finally:
        db.close()
    assert toolkit.dispatched == [("recall", {"query": "x"})]
    assert status == "executed"
    assert "resultado de recall" in result


def test_execute_proposal_cannot_run_twice():
    pulse = _pulse()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        p = pulse.propose(db, owner, "recall", {"query": "x"}, "lembrar", "r")
        asyncio.run(pulse.execute_proposal(db, owner, p.id))
        try:
            asyncio.run(pulse.execute_proposal(db, owner, p.id))
            raised = False
        except ValueError:
            raised = True
    finally:
        db.close()
    assert raised


def test_reject_proposal_marks_rejected():
    pulse = _pulse()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        p = pulse.propose(db, owner, "create_goal", {"title": "x"}, "criar", "r")
        done = pulse.reject_proposal(db, owner, p.id)
        status, decided_at = done.status, done.decided_at  # read before closing
    finally:
        db.close()
    assert status == "rejected"
    assert decided_at is not None


# ---------- API ----------

def test_agent_endpoints_require_auth(client):
    assert client.get("/api/v1/agent/pulse").status_code == 401
    assert client.get("/api/v1/agent/proposals").status_code == 401
    assert client.post("/api/v1/agent/pulse/run").status_code == 401


def test_proposals_api_approve_and_reject(client, owner_headers):
    from app.core.di import get_kernel
    from app.models.models import Owner

    db = SessionLocal()
    try:
        owner_id = db.query(Owner).first().id
        pulse = get_kernel().pulse
        assert pulse is not None, "the pulse should be wired in the test kernel"

        p_ok = pulse.propose(db, owner_id, "list_goals", {}, "revisar objetivos", "rotina")
        p_no = pulse.propose(db, owner_id, "create_goal", {"title": "não quero"}, "recusar", "r")

        listed = client.get("/api/v1/agent/proposals", headers=owner_headers).json()
        ids = {item["id"] for item in listed}
        assert {p_ok.id, p_no.id} <= ids

        r = client.post(f"/api/v1/agent/proposals/{p_ok.id}/approve", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "executed"

        r = client.post(f"/api/v1/agent/proposals/{p_no.id}/reject", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

        # already decided -> conflict
        r = client.post(f"/api/v1/agent/proposals/{p_no.id}/approve", headers=owner_headers)
        assert r.status_code == 409
        r = client.post("/api/v1/agent/proposals/fantasma/approve", headers=owner_headers)
        assert r.status_code == 404
    finally:
        db.close()


def test_pulse_run_endpoint_degrades_with_brain_offline(client, owner_headers):
    """POST /agent/pulse/run with the brain down must still answer 200 with a
    report — the tick degrades, it does not crash. Forced via brain_offline so
    the result does not depend on whether this machine happens to run Ollama."""
    from tests.conftest import brain_offline

    with brain_offline():
        r = client.post("/api/v1/agent/pulse/run", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert {"reason", "noticed", "executed", "proposed", "skipped"} <= set(body)
    assert body["executed"] == []
