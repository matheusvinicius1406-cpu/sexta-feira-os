"""
The Teia as a running platform — store, service, catalog and triggers.

These tests use the real SQLite test database (the conftest one), so they cover
persistence, the audit trail and trigger arming end to end. Kernel services are
faked, so nothing reaches Ollama or a device.
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.automation.teia import catalog
from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine import ExecutionStatus, Services, WorkflowNotFound
from app.automation.teia.service import TeiaService
from app.automation.teia.store import slugify
from app.db.database import SessionLocal
from app.models.models import AutomationExecution, AutomationNodeRun, Owner


@pytest.fixture
def owner_id(client):
    """A throwaway owner, so these tests start from an empty automation list.

    Depends on `client` on purpose: the kernel only bootstraps its own owner when
    the table is empty, so an extra owner created before boot would lock the real
    one out and break every test that logs in. Booting first removes that
    ordering hazard entirely.
    """
    db = SessionLocal()
    try:
        owner = Owner(
            id=str(uuid.uuid4()), email=f"teia-{uuid.uuid4().hex[:8]}@test.local",
            name="Teia Test", hashed_password="x", is_active=True,
        )
        db.add(owner)
        db.commit()
        return owner.id
    finally:
        db.close()


@pytest.fixture
def notifications() -> list[str]:
    return []


@pytest.fixture
def teia(notifications) -> TeiaService:
    """A service whose only real dependency is the database."""
    async def dispatch(db, owner, selector, action, params):
        notifications.append(params.get("text", ""))
        return {"ok": True, "device": "Pixel", "delivered": True}

    return TeiaService(Services(actions=SimpleNamespace(dispatch=dispatch)))


def fired_count(teia: TeiaService, moment: datetime, slug: str) -> int:
    """How many times ONE slug fired on this tick.

    The manager arms every enabled workflow in the database, so a tick may also
    fire automations left behind by other tests; only ours is asserted on.
    """
    return asyncio.run(teia.triggers.tick(moment)).count(slug)


def simple_workflow(name: str = "Teste simples") -> Workflow:
    wf = Workflow(name=name)
    start = wf.add_node("inicio", {"dados": {"origem": "teste"}}, id="a")
    text = wf.add_node("texto", {"texto": "veio de {{ nodes.a.origem }}"}, id="b")
    wf.connect(start, text)
    return wf


# ---------------------------------------------------------------- slugs


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Briefing Matinal", "briefing-matinal"),
        ("Revisão Noturna!", "revisao-noturna"),
        ("  espaços   demais  ", "espacos-demais"),
        ("já-é-slug", "ja-e-slug"),
        ("...", "automacao"),
    ],
)
def test_slugify(title, expected):
    assert slugify(title) == expected


# ---------------------------------------------------------------- store


def test_save_and_read_back(teia, owner_id):
    db = SessionLocal()
    try:
        row = teia.save(db, owner_id, simple_workflow(), description="uma descrição")
        assert row.slug == "teste-simples"

        found = teia.get(db, owner_id, "teste-simples")
        assert found["description"] == "uma descrição"
        assert found["definition"]["nodes"][0]["type"] == "inicio"
    finally:
        db.close()


def test_saving_the_same_slug_updates_in_place(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow())
        updated = simple_workflow()
        updated.add_node("nada", {}, id="c")
        teia.save(db, owner_id, updated, slug="teste-simples")

        assert len(teia.list(db, owner_id)) == 1
        assert len(teia.get(db, owner_id, "teste-simples")["definition"]["nodes"]) == 3
    finally:
        db.close()


def test_an_invalid_workflow_is_never_stored(teia, owner_id):
    wf = Workflow(name="Quebrada")
    wf.add_node("tipo_inexistente", {}, id="x")

    db = SessionLocal()
    try:
        with pytest.raises(WorkflowValidationError):
            teia.save(db, owner_id, wf)
        assert teia.get(db, owner_id, "quebrada") is None
    finally:
        db.close()


def test_list_filters_by_query(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow("Backup diário"), description="copia o banco")
        teia.save(db, owner_id, simple_workflow("Outra coisa"))
        assert [w["slug"] for w in teia.list(db, owner_id, query="backup")] == ["backup-diario"]
        assert [w["slug"] for w in teia.list(db, owner_id, query="banco")] == ["backup-diario"]
    finally:
        db.close()


def test_enable_disable_and_delete(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow())
        assert teia.set_enabled(db, owner_id, "teste-simples", False) is True
        assert teia.get(db, owner_id, "teste-simples")["enabled"] is False
        assert teia.delete(db, owner_id, "teste-simples") is True
        assert teia.get(db, owner_id, "teste-simples") is None
        assert teia.delete(db, owner_id, "teste-simples") is False
    finally:
        db.close()


# ---------------------------------------------------------------- running


def test_run_by_slug_persists_the_audit_trail(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow())
    finally:
        db.close()

    result = asyncio.run(teia.run_slug(owner_id, "teste-simples", {"quem": "eu"}))
    assert result.status is ExecutionStatus.COMPLETED
    assert result.output["b"] == [{"texto": "veio de teste"}]

    db = SessionLocal()
    try:
        stored = teia.executions.get(db, owner_id, result.execution_id)
        assert stored["status"] == "completed"
        assert stored["trigger"] == "manual"
        assert {n["node_id"] for n in stored["nodes"]} == {"a", "b"}
        assert all(n["status"] == "completed" for n in stored["nodes"])
        assert teia.store.get(db, owner_id, "teste-simples").last_run_at is not None
    finally:
        db.close()


def test_running_an_unknown_slug_lists_what_exists(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow())
    finally:
        db.close()

    with pytest.raises(WorkflowNotFound, match="teste-simples"):
        asyncio.run(teia.run_slug(owner_id, "nao-existe"))


def test_a_failed_run_is_recorded_with_its_error(teia, owner_id):
    wf = Workflow(name="Vai falhar")
    wf.add_node("parar", {"mensagem": "parei de propósito", "erro": True}, id="x")

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    result = asyncio.run(teia.run_slug(owner_id, "vai-falhar"))
    assert result.status is ExecutionStatus.FAILED

    db = SessionLocal()
    try:
        stored = teia.executions.get(db, owner_id, result.execution_id)
        assert stored["status"] == "failed"
        assert "parei de propósito" in stored["error"]
        assert stored["nodes"][0]["status"] == "failed"
    finally:
        db.close()


def test_disabled_workflows_still_run_by_hand_but_not_by_trigger(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow(), enabled=False)
    finally:
        db.close()

    assert asyncio.run(teia.run_slug(owner_id, "teste-simples")).ok is True
    with pytest.raises(WorkflowNotFound, match="desativada"):
        asyncio.run(teia.run_slug(owner_id, "teste-simples", trigger_type="agenda"))


def test_notifications_reach_the_action_service(teia, owner_id, notifications):
    wf = Workflow(name="Avisar")
    wf.add_node("notificar", {"texto": "olá do teste"}, id="x")
    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    assert asyncio.run(teia.run_slug(owner_id, "avisar")).ok
    assert notifications == ["olá do teste"]


# ---------------------------------------------------------------- composition


def test_sub_workflow_runs_another_automation(teia, owner_id):
    inner = Workflow(name="Interna")
    inner.add_node("texto", {"texto": "sou a interna"}, id="x")

    outer = Workflow(name="Externa")
    outer.add_node("sub_automacao", {"automacao": "interna"}, id="chamar")

    db = SessionLocal()
    try:
        teia.save(db, owner_id, inner)
        teia.save(db, owner_id, outer)
    finally:
        db.close()

    result = asyncio.run(teia.run_slug(owner_id, "externa"))
    assert result.status is ExecutionStatus.COMPLETED
    assert result.output["chamar"][0]["ok"] is True


def test_recursion_is_stopped_at_the_depth_limit(teia, owner_id):
    """A workflow that calls itself stops at max_depth instead of eating the box."""
    wf = Workflow(name="Recursiva")
    wf.add_node("sub_automacao", {"automacao": "recursiva"}, id="eu")

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    result = asyncio.run(teia.run_slug(owner_id, "recursiva"))
    assert result.status is ExecutionStatus.FAILED
    assert "profundidade" in result.error


# ---------------------------------------------------------------- catalog


def test_catalog_installs_and_is_idempotent(teia, owner_id):
    db = SessionLocal()
    try:
        installed = catalog.seed(teia, db, owner_id)
        assert len(installed) == len(catalog.CATALOG)
        assert catalog.seed(teia, db, owner_id) == []          # nothing new the 2nd time
        assert len(teia.list(db, owner_id)) == len(catalog.CATALOG)
    finally:
        db.close()


def test_reseeding_does_not_clobber_your_edits(teia, owner_id):
    db = SessionLocal()
    try:
        catalog.seed(teia, db, owner_id)
        mine = simple_workflow("Briefing matinal")
        teia.save(db, owner_id, mine, slug="briefing-matinal", description="do meu jeito")

        catalog.seed(teia, db, owner_id)
        assert teia.get(db, owner_id, "briefing-matinal")["description"] == "do meu jeito"
    finally:
        db.close()


def test_every_catalog_workflow_is_valid(teia):
    for slug, workflow, description, tags, _enabled in catalog.build_all():
        assert teia.validate(workflow) == [], f"'{slug}' inválida"
        assert description, f"'{slug}' está sem descrição"
        assert tags, f"'{slug}' está sem tags"


def test_catalog_workflows_declare_a_trigger():
    for slug, workflow, *_ in catalog.build_all():
        assert workflow.triggers, f"'{slug}' não tem gatilho"


def test_capture_survives_having_no_device_paired(teia, owner_id):
    """A thought already saved must not be thrown away by a failed notification.

    On a kernel with no device paired, `notificar` fails. For an automation whose
    deliverable is the capture itself, that failure is a courtesy that did not
    land — not a reason to report the run as lost.
    """
    async def refuse(db, owner, selector, action, params):
        return {"ok": False, "error": f"Nenhum dispositivo '{selector}' pareado."}

    async def remember(db, owner, content, **kw):
        return SimpleNamespace(id="mem-1", content=content, title=kw.get("title"))

    teia.services.actions = SimpleNamespace(dispatch=refuse)
    teia.services.memory = SimpleNamespace(remember=remember)

    db = SessionLocal()
    try:
        catalog.seed(teia, db, owner_id)
    finally:
        db.close()

    result = asyncio.run(
        teia.run_slug(owner_id, "captura-rapida", {"texto": "uma ideia"})
    )
    assert result.status is ExecutionStatus.COMPLETED, result.error

    by_node = {r.node_id: r.status.value for r in result.node_results}
    assert by_node["gravar"] == "completed"      # the memory was written
    assert by_node["arquivar"] == "completed"    # and so was the inbox file
    assert by_node["confirmar"] == "failed"      # the courtesy did not land


def test_a_catalog_automation_actually_runs(teia, owner_id, notifications):
    """The disk watchdog runs for real: it reads the disk and decides."""
    db = SessionLocal()
    try:
        catalog.seed(teia, db, owner_id)
    finally:
        db.close()

    result = asyncio.run(teia.run_slug(owner_id, "vigia-do-disco"))
    assert result.status is ExecutionStatus.COMPLETED


# ---------------------------------------------------------------- triggers


def test_reload_arms_only_enabled_workflows(teia, owner_id):
    wf = Workflow(name="Agendada")
    node = wf.add_node("texto", {"texto": "oi"}, id="x")
    wf.add_trigger("agenda", node, {"cron": "0 7 * * *"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
        assert any(a.slug == "agendada" for a in teia.triggers.armed)

        teia.set_enabled(db, owner_id, "agendada", False)
        assert not any(a.slug == "agendada" for a in teia.triggers.armed)
    finally:
        db.close()


def test_a_broken_cron_is_skipped_without_blinding_the_others(teia, owner_id):
    """A hand-edited definition with a bad cron must not disarm everything else."""
    good = Workflow(name="Boa")
    good_node = good.add_node("texto", {"texto": "oi"}, id="x")
    good.add_trigger("agenda", good_node, {"cron": "0 7 * * *"})

    broken = Workflow(name="Cron ruim")
    broken_node = broken.add_node("texto", {"texto": "oi"}, id="x")
    broken.add_trigger("agenda", broken_node, {"cron": "0 7 * * *"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, good)
        row = teia.save(db, owner_id, broken)

        # Corrupt the stored cron the way a manual edit would.
        definition = json.loads(row.definition)
        definition["triggers"][0]["config"]["cron"] = "isso não é cron"
        row.definition = json.dumps(definition, ensure_ascii=False)
        db.commit()

        teia.triggers.reload()
        armed = {a.slug for a in teia.triggers.armed}
        assert "cron-ruim" not in armed
        assert "boa" in armed
    finally:
        db.close()


def test_cron_fires_once_per_minute_even_across_a_reload(teia, owner_id):
    wf = Workflow(name="A cada minuto")
    node = wf.add_node("texto", {"texto": "tick"}, id="x")
    wf.add_trigger("agenda", node, {"cron": "* * * * *"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    now = datetime.now().astimezone().replace(second=0, microsecond=0)
    assert fired_count(teia, now, "a-cada-minuto") == 1

    # Same minute, and the manager's memory was wiped by a reload: the audit
    # trail is what stops the double fire.
    teia.triggers.reload()
    assert fired_count(teia, now + timedelta(seconds=20), "a-cada-minuto") == 0

    # Next minute fires again.
    assert fired_count(teia, now + timedelta(minutes=1), "a-cada-minuto") == 1


def test_interval_trigger_respects_its_period(teia, owner_id):
    wf = Workflow(name="Cada minuto e meio")
    node = wf.add_node("texto", {"texto": "tick"}, id="x")
    wf.add_trigger("intervalo", node, {"segundos": 90})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    now = datetime.now().astimezone()
    assert fired_count(teia, now, "cada-minuto-e-meio") == 1
    assert fired_count(teia, now + timedelta(seconds=60), "cada-minuto-e-meio") == 0
    assert fired_count(teia, now + timedelta(seconds=95), "cada-minuto-e-meio") == 1


def test_webhook_lookup(teia, owner_id):
    wf = Workflow(name="Gancho")
    node = wf.add_node("texto", {"texto": "recebi"}, id="x")
    wf.add_trigger("webhook", node, {"caminho": "meu-gancho"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    armed = teia.triggers.find_webhook("meu-gancho")
    assert armed is not None and armed.slug == "gancho"
    assert teia.triggers.find_webhook("/meu-gancho/") is not None    # slashes tolerated
    assert teia.triggers.find_webhook("outro") is None


def test_event_trigger_fires_a_matching_automation(teia, owner_id, notifications):
    wf = Workflow(name="Reage")
    node = wf.add_node("notificar", {"texto": "evento: {{ trigger.evento }}"}, id="x")
    wf.add_trigger("evento", node, {"tipo": "objetivo.*"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    event = SimpleNamespace(
        id="ev1", owner_id=owner_id, type="objetivo.concluido",
        source="planning", payload='{"title": "estudar"}',
    )

    async def scenario():
        teia.triggers.on_event(None, event)
        await teia.triggers.drain()

    asyncio.run(scenario())
    assert notifications == ["evento: objetivo.concluido"]


def test_an_automation_does_not_retrigger_itself(teia, owner_id, notifications):
    wf = Workflow(name="Eco")
    node = wf.add_node("notificar", {"texto": "eco"}, id="x")
    wf.add_trigger("evento", node, {"tipo": "*"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    own_event = SimpleNamespace(
        id="ev1", owner_id=owner_id, type="qualquer.coisa",
        source="teia:eco", payload=None,
    )

    async def scenario():
        teia.triggers.on_event(None, own_event)
        await teia.triggers.drain()

    asyncio.run(scenario())
    assert notifications == []


def test_event_triggers_are_rate_limited(teia, owner_id, notifications, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "teia_event_fires_per_minute", 3)

    wf = Workflow(name="Barulhenta")
    node = wf.add_node("notificar", {"texto": "ping"}, id="x")
    wf.add_trigger("evento", node, {"tipo": "ping.*"})

    db = SessionLocal()
    try:
        teia.save(db, owner_id, wf)
    finally:
        db.close()

    event = SimpleNamespace(
        id="e", owner_id=owner_id, type="ping.recebido", source="kernel", payload=None
    )

    async def scenario():
        for _ in range(10):
            teia.triggers.on_event(None, event)
        await teia.triggers.drain()

    asyncio.run(scenario())
    assert len(notifications) == 3


# ---------------------------------------------------------------- status


def test_status_describes_the_engine(teia):
    status = asyncio.run(teia.status())
    assert status["engine"] == "teia"
    assert status["online"] is True
    assert status["node_types"] >= 40
    assert status["trigger_types"] == 5


def test_cancelling_an_execution_that_is_not_running_returns_false(teia):
    assert teia.cancel("nao-existe") is False


def test_node_runs_are_scoped_to_their_execution(teia, owner_id):
    db = SessionLocal()
    try:
        teia.save(db, owner_id, simple_workflow())
    finally:
        db.close()

    first = asyncio.run(teia.run_slug(owner_id, "teste-simples"))
    second = asyncio.run(teia.run_slug(owner_id, "teste-simples"))

    db = SessionLocal()
    try:
        assert db.query(AutomationExecution).filter(
            AutomationExecution.id.in_([first.execution_id, second.execution_id])
        ).count() == 2
        assert db.query(AutomationNodeRun).filter(
            AutomationNodeRun.execution_id == first.execution_id
        ).count() == 2
    finally:
        db.close()
