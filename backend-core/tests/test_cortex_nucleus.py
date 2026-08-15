"""
Núcleo decisório — regras + metas + contexto num ciclo único, sem LLM.

Provas do contrato: o núcleo une as duas vozes (regra forte do mundo vence o
foco; senão o foco rankeado; senão "nenhuma"), persiste como Decision
(question="nucleo", auditável em /decision/history), e o racional explica
qual voz venceu e por quê.
"""
import asyncio
import uuid

from app.cortex.nucleus import decidir
from app.decision.service import DecisionEngine
from app.planning.service import PlanningEngine
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


def _engine():
    return DecisionEngine(planning=PlanningEngine(), world=WorldModel())


# ── rank_goals: avalia sem persistir ──────────────────────


def test_rank_goals_does_not_persist():
    engine = _engine()
    owner = f"o-{uuid.uuid4().hex}"
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        asyncio.run(engine.planning.create_goal(db, owner, "Meta", priority=5))
        scored, policy, weights = engine.rank_goals(db, owner)
        history = engine.history(db, owner)
    finally:
        db.close()
    assert scored and scored[0]["label"] == "Meta"
    assert policy == "default" and weights
    assert history == []  # rankeou sem gravar nada


# ── fusão: regra forte vence o foco ───────────────────────


def test_strong_rule_wins_over_goal():
    engine = _engine()
    owner = f"o-{uuid.uuid4().hex}"
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        asyncio.run(engine.planning.create_goal(db, owner, "Meta prioritária", priority=5))
        out = asyncio.run(decidir(
            db, owner, engine,
            contexto={"agora": {"hora": 23, "dia_semana": "sexta"},
                      "radio": {"tocando": True, "fila": 2}},
        ))
        escolha = out["escolha"]
    finally:
        db.close()
    # madrugada-silencio (p30) dispara de madrugada com música tocando
    assert escolha["tipo"] == "regra"
    assert escolha["alvo"] == "madrugada-silencio"
    assert escolha["rationale"]
    assert out["regras"]["dispararam"] >= 1


# ── fusão: sem regra forte, o foco rankeado vence ─────────


def test_goal_focus_when_no_strong_rule():
    engine = _engine()
    owner = f"o-{uuid.uuid4().hex}"
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        asyncio.run(engine.planning.create_goal(db, owner, "Meta única", priority=5))
        out = asyncio.run(decidir(
            db, owner, engine,
            # tarde da tarde, sem música, domingo — nenhuma regra forte (>= p20)
            contexto={"agora": {"hora": 15, "dia_semana": "domingo"},
                      "radio": {"tocando": False, "fila": 0}},
        ))
        escolha = out["escolha"]
    finally:
        db.close()
    assert escolha["tipo"] == "foco"
    assert escolha["descricao"] == "Meta única"
    assert out["foco"]["label"] == "Meta única"


# ── fusão: nada exigindo decisão ──────────────────────────


def test_nothing_to_decide():
    engine = _engine()
    owner = f"o-{uuid.uuid4().hex}"
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        out = asyncio.run(decidir(
            db, owner, engine,
            contexto={"agora": {"hora": 15, "dia_semana": "domingo"},
                      "radio": {"tocando": False, "fila": 0}},
        ))
        escolha = out["escolha"]
    finally:
        db.close()
    assert escolha["tipo"] == "nenhuma"
    assert "nada exige" in escolha["descricao"].lower()


# ── persistência + trilha ─────────────────────────────────


def test_nucleus_persists_decision_with_trail():
    engine = _engine()
    owner = f"o-{uuid.uuid4().hex}"
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        out = asyncio.run(decidir(
            db, owner, engine,
            contexto={"agora": {"hora": 15, "dia_semana": "domingo"},
                      "radio": {"tocando": False, "fila": 0}},
        ))
        did = out["decisao_id"]
        hist = [d for d in engine.history(db, owner) if d.question == "nucleo"]
    finally:
        db.close()
    assert hist and hist[0].id == did
    assert hist[0].policy == "nenhuma"
    assert out["regras"]["trail"]  # trilha condição por condição anexada


def test_nucleus_rule_choice_sets_foco_fact_only_for_goals():
    engine = _engine()
    owner = f"o-{uuid.uuid4().hex}"
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        asyncio.run(decidir(
            db, owner, engine,
            contexto={"agora": {"hora": 23, "dia_semana": "sexta"},
                      "radio": {"tocando": True, "fila": 2}},
        ))
        fact = engine.world.get_fact(db, owner, "foco_decidido")
    finally:
        db.close()
    assert fact is None  # regra venceu: não sobrescreve o foco do dono


# ── API ───────────────────────────────────────────────────


def test_decidir_endpoint_regra(client, owner_headers):
    r = client.post(
        "/api/v1/cortex/decidir",
        json={"contexto": {"agora": {"hora": 23, "dia_semana": "sexta"},
                           "radio": {"tocando": True, "fila": 3}}},
        headers=owner_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["escolha"]["tipo"] == "regra"
    assert body["escolha"]["alvo"] == "madrugada-silencio"
    assert body["escolha"]["rationale"]
    assert body["regras"]["total"] >= 10
    assert body["regras"]["trail"]


def test_decidir_ultimo_endpoint(client, owner_headers):
    client.post(
        "/api/v1/cortex/decidir",
        json={"contexto": {"agora": {"hora": 15, "dia_semana": "domingo"},
                           "radio": {"tocando": False, "fila": 0}}},
        headers=owner_headers,
    )
    r = client.get("/api/v1/cortex/decidir/ultimo", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["decisao"] is not None
    assert body["decisao"]["question"] == "nucleo"
    assert body["decisao"]["rationale"]
