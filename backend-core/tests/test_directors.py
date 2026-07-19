"""
Directors — contract and API tests.

Deterministic (no Ollama): a scripted fake brain drives the tool loop. They prove
the cabinet seeds idempotently, expertise accumulates per director (and per
owner) on the shared Memory substrate, delegation runs with a restricted toolset,
recursion is hard-stopped, consolidation stores the takeaway back into the
director, and everything is announced as events.
"""
import asyncio
import uuid

from app.brain.memory import PersistentMemory
from app.db.database import SessionLocal
from app.directors.service import DEFAULT_DIRECTORS, DirectorService
from app.events.bus import EventBus

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


class _FakeBrain:
    """Scripted LocalBrain: pops chat_with_tools replies; fixed chat reply."""

    def __init__(self, tool_replies: list[dict], chat_reply: str = "NADA"):
        self.tool_replies = list(tool_replies)
        self.chat_reply = chat_reply

    async def chat_with_tools(self, messages, tools=None):
        return self.tool_replies.pop(0) if self.tool_replies else {"content": ""}

    async def chat(self, messages, temperature=0.1, max_tokens=80):
        return self.chat_reply

    async def embed(self, text):
        raise RuntimeError("offline")  # memory stores without a vector (graceful)


class _SpyToolkit:
    """ToolKit stand-in: records dispatches, returns a canned tool result."""

    def __init__(self):
        self.dispatched: list[str] = []

    async def specs_subset(self, allowed):
        return [{"type": "function", "function": {"name": n}} for n in allowed]

    async def dispatch(self, name, args, db, owner_id):
        self.dispatched.append(name)
        return f"resultado de {name}"


def _service(brain=None, toolkit=None, events=None) -> DirectorService:
    brain = brain or _FakeBrain([])
    return DirectorService(
        brain, toolkit or _SpyToolkit(), PersistentMemory(brain), events=events
    )


# ---------- cabinet ----------

def test_ensure_defaults_seeds_canonical_cabinet_idempotently():
    svc = _service()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        first = svc.ensure_defaults(db, owner)
        second = svc.ensure_defaults(db, owner)
        names = {d.name for d in svc.list(db, owner)}
    finally:
        db.close()
    assert first == len(DEFAULT_DIRECTORS)
    assert second == 0                                   # idempotent
    assert {"engenharia", "seguranca", "memoria"} <= names


def test_create_is_upsert_by_name():
    svc = _service()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        a = svc.create(db, owner, "financeiro", "Diretor Financeiro", "gastos")
        b = svc.create(db, owner, "financeiro", "Diretor Financeiro", "gastos e investimentos")
        count = len([d for d in svc.list(db, owner) if d.name == "financeiro"])
        domain = svc.get(db, owner, "financeiro").domain
    finally:
        db.close()
    assert a.id == b.id
    assert count == 1
    assert domain == "gastos e investimentos"


# ---------- specialized memory ----------

def test_expertise_is_scoped_per_director_and_owner():
    svc = _service()
    a, b = f"o-{uuid.uuid4().hex}", f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(svc.teach(db, a, "engenharia", "usar migrações sempre"))
        asyncio.run(svc.teach(db, a, "seguranca", "nunca logar segredos"))
        asyncio.run(svc.teach(db, b, "engenharia", "coisa do outro dono"))
        eng_a = [m.content for m in svc.expertise(db, a, "engenharia")]
        sec_a = [m.content for m in svc.expertise(db, a, "seguranca")]
    finally:
        db.close()
    assert eng_a == ["usar migrações sempre"]            # not the other director's...
    assert sec_a == ["nunca logar segredos"]             # ...nor the other owner's


# ---------- delegation ----------

def test_delegate_runs_tools_consolidates_and_emits():
    brain = _FakeBrain(
        tool_replies=[
            {"content": "", "tool_calls": [
                {"function": {"name": "recall", "arguments": {"query": "x"}}}]},
            {"content": "Análise concluída: use SQLite."},
        ],
        chat_reply="Para bancos locais de um dono, SQLite basta.",
    )
    toolkit = _SpyToolkit()
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("diretor.*", lambda db, ev: seen.append(ev.type))
    svc = DirectorService(brain, toolkit, PersistentMemory(brain), events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        svc.ensure_defaults(db, owner)
        result = asyncio.run(svc.delegate(db, owner, "engenharia", "qual banco usar?"))
        lessons = [m.content for m in svc.expertise(db, owner, "engenharia")]
    finally:
        db.close()
    assert result == "Análise concluída: use SQLite."
    assert toolkit.dispatched == ["recall"]              # restricted toolset was used
    assert "Para bancos locais de um dono, SQLite basta." in lessons  # learning stays
    assert seen == ["diretor.delegado", "diretor.concluido"]


def test_delegate_hard_stops_recursion():
    brain = _FakeBrain(
        tool_replies=[
            {"content": "", "tool_calls": [
                {"function": {"name": "consult_director",
                              "arguments": {"director": "pesquisa", "task": "loop"}}}]},
            {"content": "Feito sem delegar."},
        ],
    )
    toolkit = _SpyToolkit()
    svc = DirectorService(brain, toolkit, PersistentMemory(brain))
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        svc.ensure_defaults(db, owner)
        result = asyncio.run(svc.delegate(db, owner, "engenharia", "tarefa"))
    finally:
        db.close()
    assert result == "Feito sem delegar."
    assert toolkit.dispatched == []                      # the blocked tool never ran


def test_delegate_unknown_director_lists_cabinet():
    svc = _service()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        svc.ensure_defaults(db, owner)
        result = asyncio.run(svc.delegate(db, owner, "inexistente", "tarefa"))
    finally:
        db.close()
    assert "não existe" in result
    assert "engenharia" in result


# ---------- API ----------

def test_directors_require_auth(client):
    assert client.get("/api/v1/directors").status_code == 403


def test_directors_api_cabinet_teach_and_memory(client, owner_headers):
    cabinet = client.get("/api/v1/directors", headers=owner_headers).json()
    assert {d["name"] for d in cabinet} >= {"engenharia", "pesquisa", "seguranca"}

    r = client.post("/api/v1/directors", headers=owner_headers, json={
        "name": "juridico", "title": "Diretor Jurídico",
        "domain": "contratos e leis (auxílio, nunca substitui profissionais)",
    })
    assert r.status_code == 200

    client.post("/api/v1/directors/juridico/memory",
                json={"content": "sempre ler a licença antes de copiar código"},
                headers=owner_headers)
    mem = client.get("/api/v1/directors/juridico/memory", headers=owner_headers).json()
    assert any("licença" in m["content"] for m in mem)

    assert client.get("/api/v1/directors/fantasma/memory",
                      headers=owner_headers).status_code == 404


def test_delegate_degrades_gracefully_without_brain(client, owner_headers):
    r = client.post("/api/v1/directors/engenharia/delegate",
                    json={"task": "qualquer coisa"}, headers=owner_headers)
    assert r.status_code == 503                          # brain offline -> clean 503
