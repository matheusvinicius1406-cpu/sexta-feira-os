"""
Regras → pulse: regra disparada vira PROPOSTA do agente, com a trilha anexada.

Provas do contrato: cada regra disparada vira proposta pending (source="cortex")
com o "por que" no reason e a ação pronta para executar via toolkit; repetição
não duplica (dedupe); regra `auto: true` executa na hora pelo mesmo rastro; e a
aprovação do dono dispara a MESMA tool (cortex_regra) pelo mesmo dispatch.
"""
import asyncio
import json
import uuid

from app.agent.pulse import CognitivePulse
from app.brain.tools import ToolKit
from app.cortex.nucleus import propor_regras
from app.cortex.rules import Rule
from app.db.database import SessionLocal

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


class _FakeBrain:
    async def chat(self, messages, temperature=0.2, max_tokens=250, **kwargs):
        return '{"nothing": true}'


class _SpyToolkit:
    def __init__(self):
        self.dispatched: list[tuple[str, dict]] = []

    async def dispatch(self, name, args, db, owner_id):
        self.dispatched.append((name, args))
        return f"resultado de {name}"


def _pulse(toolkit=None) -> CognitivePulse:
    return CognitivePulse(
        _FakeBrain(), toolkit or _SpyToolkit(),
        world=None, planning=None, decision=None, learning=None,
        events=None, journal=None,
    )


def _madrugada():
    return {"agora": {"hora": 23, "dia_semana": "sexta"},
            "radio": {"tocando": True, "fila": 3}}


def test_propor_regras_cria_propostas_com_trilha():
    pulse = _pulse()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        out = asyncio.run(propor_regras(db, owner, pulse, contexto=_madrugada()))
        pend = pulse.list_proposals(db, owner, status="pending")
    finally:
        db.close()
    assert out["propostas_criadas"]
    assert len(pend) == len(out["propostas_criadas"])
    p = next(x for x in pend if "madrugada-silencio" in (x.reason or ""))
    assert p.tool == "cortex_regra"
    assert p.reason and "por que:" in p.reason
    assert "(p30)" in p.reason  # a regra e a prioridade na trilha
    assert json.loads(p.tool_args)["acao"]["tipo"] == "sugestao"


def test_propor_regras_dedupe_nao_duplica():
    pulse = _pulse()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        first = asyncio.run(propor_regras(db, owner, pulse, contexto=_madrugada()))
        second = asyncio.run(propor_regras(db, owner, pulse, contexto=_madrugada()))
        pend = pulse.list_proposals(db, owner, status="pending")
    finally:
        db.close()
    assert second["puladas_por_dedupe"] >= 1
    assert len(pend) == len(first["propostas_criadas"])  # nada duplicado


def test_propor_regras_nada_disparado_nao_cria_proposta():
    pulse = _pulse()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        out = asyncio.run(propor_regras(
            db, owner, pulse,
            contexto={"agora": {"hora": 15, "dia_semana": "domingo"},
                      "radio": {"tocando": False, "fila": 0}},
        ))
        pend = pulse.list_proposals(db, owner)
    finally:
        db.close()
    assert out["propostas_criadas"] == []
    assert pend == []


def test_regra_auto_executa_na_hora_pelo_mesmo_rastro(monkeypatch):
    auto = Rule(
        id="auto-fala", description="Regra auto", priority=30, auto=True,
        when={"sempre": True}, then={"falar": "bom dia"},
    )
    monkeypatch.setattr("app.cortex.nucleus.load_rules", lambda: [auto])
    toolkit = _SpyToolkit()
    pulse = _pulse(toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        out = asyncio.run(propor_regras(db, owner, pulse, contexto={}))
        pend = pulse.list_proposals(db, owner)
    finally:
        db.close()
    assert out["auto_executadas"] == out["propostas_criadas"]
    assert pend and pend[0].status == "executed"  # nunca ficou pendente
    assert toolkit.dispatched == [("cortex_regra", {"acao": {"tipo": "falar", "valor": "bom dia"}})]


def test_aprovacao_executa_tool_cortex_regra():
    toolkit = _SpyToolkit()
    pulse = _pulse(toolkit=toolkit)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        out = asyncio.run(propor_regras(db, owner, pulse, contexto=_madrugada()))
        pid = out["propostas_criadas"][0]
        done = asyncio.run(pulse.execute_proposal(db, owner, pid))
        status = done.status
    finally:
        db.close()
    assert status == "executed"
    assert toolkit.dispatched and toolkit.dispatched[0][0] == "cortex_regra"


# ── toolkit real: dispatch de cortex_regra ────────────────


class _FakeLearning:
    async def record(self, db, owner_id, context, observation=None,
                     quality=0.5, lesson=None, tag=None, source="tool"):
        return type("E", (), {"quality": quality})()


class _FakeAutomations:
    pass


def test_dispatch_sugestao_registra_aprendizado():
    tk = ToolKit(memory=None, automations=_FakeAutomations(), learning=_FakeLearning())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        result = asyncio.run(tk.dispatch(
            "cortex_regra",
            {"acao": {"tipo": "sugestao", "valor": "está tarde"}},
            db, owner,
        ))
    finally:
        db.close()
    assert "Aprendizado registrado" in result


def test_dispatch_intent_hora():
    tk = ToolKit(memory=None, automations=_FakeAutomations(), learning=_FakeLearning())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        result = asyncio.run(tk.dispatch(
            "cortex_regra",
            {"acao": {"tipo": "intent", "valor": {"verb": "hora", "target": None}}},
            db, owner,
        ))
    finally:
        db.close()
    assert "São" in result  # a intenção hora roda nas engines reais


def test_dispatch_falar_devolve_texto():
    tk = ToolKit(memory=None, automations=_FakeAutomations(), learning=_FakeLearning())
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        result = asyncio.run(tk.dispatch(
            "cortex_regra",
            {"acao": {"tipo": "falar", "valor": "bom dia"}},
            db, owner,
        ))
    finally:
        db.close()
    assert result == "Jarvis diria: bom dia"


# ── API ───────────────────────────────────────────────────


def test_regras_propor_endpoint_cria_e_aprova(client, owner_headers):
    r = client.post(
        "/api/v1/cortex/regras/propor",
        json={"contexto": _madrugada()},
        headers=owner_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["propostas_criadas"]
    assert body["regras"]["dispararam"] >= 1

    pid = body["propostas_criadas"][0]
    r = client.post(f"/api/v1/agent/proposals/{pid}/approve", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "executed"

    # dedupe: propor de novo não cria duplicata
    r2 = client.post(
        "/api/v1/cortex/regras/propor",
        json={"contexto": _madrugada()},
        headers=owner_headers,
    )
    assert r2.json()["puladas_por_dedupe"] >= 1
