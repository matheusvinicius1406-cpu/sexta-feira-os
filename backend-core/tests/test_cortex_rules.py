"""
Regras declarativas do cortex — decisão com trilha. Estas provas fixam o
contrato: YAML vira regra sem virar código (ação desconhecida = erro), cada
condição deixa o valor observado na trilha, e regra com dado indisponível
falha com o motivo — nunca inventa medição.
"""
import pytest

from app.cortex.rules import Rule, RuleError, eval_conditions, evaluate, load_rules


def _ctx(**kw):
    base = {
        "agora": {"hora": 23, "dia_semana": "sexta"},
        "radio": {"tocando": True, "faixa": "Antena 1", "fila": 2},
        "voz": {"pack": "jarvis"},
        "sistema": {"cpu_percent": 40.0},
        "metas": {"ativas": 1},
        "memoria": {"total": 5},
    }
    base.update(kw)
    return base


# ── carregamento ──────────────────────────────────────────


def test_default_rules_load():
    rules = load_rules()
    assert len(rules) >= 5
    ids = {r.id for r in rules}
    assert {"madrugada-silencio", "madrugada-calma", "manha-bom-dia", "cpu-em-alta"} <= ids
    for r in rules:
        assert r.description
        assert r.when and r.then
        assert r.auto is False  # padrão seguro: propõe, não executa


def test_unknown_operator_is_rejected(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(
        "id: quebrada\n"
        "descricao: condição inexistente\n"
        "when:\n"
        "  hora_fantasma: 3\n"
        "then:\n"
        "  sugestao: x\n",
        encoding="utf-8",
    )
    with pytest.raises(RuleError, match="hora_fantasma"):
        load_rules(f)


def test_unknown_action_is_rejected(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(
        "id: perigosa\n"
        "descricao: ação fora do contrato\n"
        "when:\n"
        "  sempre: true\n"
        "then:\n"
        "  exec: rm -rf /\n",
        encoding="utf-8",
    )
    with pytest.raises(RuleError, match="exec"):
        load_rules(f)


# ── condições ─────────────────────────────────────────────


def test_hora_entre_sem_wraparound():
    r = Rule(id="t", description="t", when={"hora_entre": [6, 12]}, then={"sugestao": "x"})
    assert eval_conditions(r, _ctx(agora={"hora": 8}))[0]["passou"] is True
    assert eval_conditions(r, _ctx(agora={"hora": 12}))[0]["passou"] is False  # [6,12)
    assert eval_conditions(r, _ctx(agora={"hora": 5}))[0]["passou"] is False


def test_hora_entre_wraparound_meia_noite():
    r = Rule(id="t", description="t", when={"hora_entre": [23, 6]}, then={"sugestao": "x"})
    for hora, esperado in [(23, True), (0, True), (5, True), (6, False), (22, False), (12, False)]:
        assert eval_conditions(r, _ctx(agora={"hora": hora}))[0]["passou"] is esperado, hora


def test_dia_semana_matches():
    r = Rule(id="t", description="t", when={"dia_semana": ["sexta"]}, then={"sugestao": "x"})
    assert eval_conditions(r, _ctx(agora={"dia_semana": "sexta"}))[0]["passou"] is True
    assert eval_conditions(r, _ctx(agora={"dia_semana": "domingo"}))[0]["passou"] is False


def test_radio_voz_cpu_conditions():
    r = Rule(
        id="t", description="t",
        when={"radio_tocando": True, "voz_pack": "jarvis", "cpu_maior_que": 30},
        then={"sugestao": "x"},
    )
    ds = eval_conditions(r, _ctx())
    assert [d["passou"] for d in ds] == [True, True, True]

    r2 = Rule(
        id="t2", description="t2",
        when={"radio_tocando": True, "voz_pack": "ultron"},
        then={"sugestao": "x"},
    )
    ds2 = eval_conditions(r2, _ctx())
    assert ds2[1]["passou"] is False
    assert "ultron" in ds2[1]["detalhe"]


def test_unavailable_data_fails_with_reason():
    r = Rule(id="t", description="t", when={"cpu_maior_que": 90}, then={"sugestao": "x"})
    ds = eval_conditions(r, _ctx(sistema={}))  # sistema ausente
    assert ds[0]["passou"] is False
    assert "indisponível" in ds[0]["detalhe"]


# ── avaliação com trilha ──────────────────────────────────


def test_evaluate_fires_with_trail():
    rules = load_rules()
    result = evaluate(rules, _ctx(agora={"hora": 23, "dia_semana": "sexta"}))
    fired = {d["regra"] for d in result["decisions"]}
    assert "madrugada-silencio" in fired
    assert "manha-bom-dia" not in fired

    # trilha: a regra disparada deixa o detalhe de CADA condição
    trail = {t["regra"]: t for t in result["trail"]}
    conds = trail["madrugada-silencio"]["condicoes"]
    assert len(conds) == 2
    hora = next(c for c in conds if c["condicao"] == "hora_entre")
    assert hora["passou"] is True
    assert "hora=23" in hora["detalhe"]
    assert trail["madrugada-silencio"]["disparou"] is True


def test_priority_orders_decisions():
    rules = load_rules()
    result = evaluate(rules, _ctx(agora={"hora": 23, "dia_semana": "sexta"}))
    ordem = [d["regra"] for d in result["decisions"]]
    assert ordem.index("madrugada-silencio") < ordem.index("madrugada-calma")
    assert result["decisions"][0]["prioridade"] == max(d["prioridade"] for d in result["decisions"])


def test_all_default_rules_propose_never_execute():
    rules = load_rules()
    result = evaluate(rules, _ctx(agora={"hora": 23, "dia_semana": "sexta"}))
    assert all(d["auto"] is False for d in result["decisions"])
    assert all("executado" not in d for d in result["decisions"])


# ── API ───────────────────────────────────────────────────


def test_rules_endpoint_lists_rules(client, owner_headers):
    r = client.get("/api/v1/cortex/rules", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 5
    ids = {g["id"] for g in body["regras"]}
    assert "madrugada-silencio" in ids
    regra = next(g for g in body["regras"] if g["id"] == "madrugada-silencio")
    assert regra["auto"] is False
    assert regra["condicoes"] == {"hora_entre": [23, 6], "radio_tocando": True}


def test_evaluate_endpoint_with_simulated_context(client, owner_headers):
    r = client.post(
        "/api/v1/cortex/rules/avaliar",
        json={"contexto": {"agora": {"hora": 23, "dia_semana": "sexta"}, "radio": {"tocando": True, "fila": 2}}},
        headers=owner_headers,
    )
    assert r.status_code == 200
    body = r.json()
    fired = {d["regra"] for d in body["decisions"]}
    assert "madrugada-silencio" in fired
    assert body["trail"]
    # trilha mostra por quê: condição com valor observado
    trail = {t["regra"]: t for t in body["trail"]}
    conds = trail["madrugada-silencio"]["condicoes"]
    assert any(c["passou"] for c in conds)


def test_evaluate_endpoint_with_real_context(client, owner_headers):
    r = client.post("/api/v1/cortex/rules/avaliar", json={}, headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["decisions"], list)
    assert isinstance(body["trail"], list)
    assert "contexto" in body  # snapshot real montado pelo kernel
    assert "agora" in body["contexto"]
