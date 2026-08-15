"""
Rules — a camada de decisão declarativa do cortex.

Regras vivem em arquivos YAML (`backend-core/rules/`) e dizem "quando
<condição>, então <ação>". O motor avalia cada regra contra um snapshot de
contexto e devolve decisões com trilha: para cada condição, o valor observado
e se passou — o "por que decidi" de verdade, auditável.

Regras NUNCA executam código arbitrário: `then` só aceita ações de um
conjunto fixo (`falar`, `sugestao`, `observar`, `intent`), e `auto` controla
se a regra executa sozinha ou propõe. Condição que depende de um dado
indisponível (sensor ausente, engine desligada) falha com o motivo na trilha —
o mesmo princípio de honestidade do resto do kernel: nunca inventar medição.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger("sexta-feira.cortex.rules")

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"

# Ações permitidas em `then` — nada além disso é aceito (sem execução
# arbitrária: uma regra YAML não vira código).
_ACTION_KEYS = {"falar", "sugestao", "observar", "intent"}

# Operadores de condição conhecidos — usados para a trilha honesta ("o que
# eu procurei") e para rejeitar YAML que nomeie operador inexistente.
_CONDITION_OPS = {
    "sempre",
    "nunca",
    "hora_entre",
    "dia_semana",
    "radio_tocando",
    "radio_fila_maior_que",
    "voz_pack",
    "cpu_maior_que",
    "metas_ativas_maior_que",
    "memorias_maior_que",
    # mundo / marcadores / timer / memória semântica
    "fato_igual",
    "fato_existe",
    "marcador_existe",
    "marcadores_maior_que",
    "timer_rodando",
    "timer_label",
    "memoria_tem",
}

_WEEKDAYS = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3,
    "sexta": 4, "sabado": 5, "domingo": 6,
}


class RuleError(ValueError):
    """Regra inválida (YAML fora do contrato) — carregar falha alto, não engole."""


@dataclass
class Rule:
    id: str
    description: str
    when: dict
    then: dict
    priority: int = 0
    auto: bool = False
    source: str = ""

    def actions(self) -> list[dict]:
        return [
            {"tipo": k, "valor": v}
            for k, v in self.then.items()
            if k in _ACTION_KEYS
        ]


def _require_str(rule_id: str, field: str, value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleError(f"regra '{rule_id}': '{field}' precisa ser texto não vazio")
    return value.strip()


def _parse_rule(raw: dict, source: str) -> Rule:
    rid = str(raw.get("id", "")).strip()
    if not rid:
        raise RuleError(f"regra sem 'id' em {source}")
    when = raw.get("when")
    then = raw.get("then")
    if not isinstance(when, dict) or not when:
        raise RuleError(f"regra '{rid}': 'when' precisa ser um mapa com condições")
    if not isinstance(then, dict) or not then:
        raise RuleError(f"regra '{rid}': 'then' precisa ter ao menos uma ação")
    unknown_ops = set(when) - _CONDITION_OPS
    if unknown_ops:
        raise RuleError(f"regra '{rid}': operador de condição desconhecido {sorted(unknown_ops)}")
    unknown_acts = set(then) - _ACTION_KEYS - {"prioridade", "auto"}
    if unknown_acts:
        raise RuleError(f"regra '{rid}': ação desconhecida {sorted(unknown_acts)}")
    return Rule(
        id=rid,
        description=_require_str(rid, "descricao", raw.get("descricao", "")),
        when=when,
        then=then,
        priority=int(raw.get("prioridade", 0) or 0),
        auto=bool(raw.get("auto", False)),
        source=source,
    )


def load_rules(path: Path | None = None) -> list[Rule]:
    """Carrega todos os `*.yaml` do diretório de regras (ou um arquivo único)."""
    root = path or RULES_DIR
    files = [root] if root.is_file() else sorted(root.glob("*.yaml"))
    rules: list[Rule] = []
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        except yaml.YAMLError as e:
            raise RuleError(f"{f.name}: YAML inválido: {e}") from e
        if isinstance(data, dict):
            data = [data]  # um arquivo pode ser uma regra única
        if not isinstance(data, list):
            raise RuleError(f"{f.name}: esperava uma lista de regras")
        for item in data:
            rules.append(_parse_rule(item, f.name))
    if not rules:
        logger.warning("nenhuma regra carregada de %s", root)
    return rules


# ── avaliação de condições ─────────────────────────────────


def _obs(ctx: dict, *path: str):
    """Lê um caminho do contexto com tolerância a ausência."""
    cur: object = ctx
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _eval_one(op: str, expected, ctx: dict) -> tuple[bool, str]:
    """Avalia UMA condição. Devolve (passou, detalhe para a trilha)."""
    if op == "sempre":
        return bool(expected), f"sempre={expected}"
    if op == "nunca":
        return not bool(expected), f"nunca={expected}"

    if op == "hora_entre":
        hora = _obs(ctx, "agora", "hora")
        lo, hi = expected[0], expected[1]
        if hora is None:
            return False, f"hora={hora} (indisponível)"
        inside = lo <= hora < hi if lo <= hi else (hora >= lo or hora < hi)
        return inside, f"hora={hora} ∈ [{lo},{hi})"

    if op == "dia_semana":
        dia = _obs(ctx, "agora", "dia_semana")
        nomes = [str(d).lower() for d in expected]
        if dia is None:
            return False, f"dia_semana={dia} (indisponível)"
        idx = _WEEKDAYS.get(dia.lower())
        ok = idx is not None and idx in {_WEEKDAYS[n] for n in nomes if n in _WEEKDAYS}
        return ok, f"dia_semana={dia} ∈ {nomes}"

    if op == "radio_tocando":
        cur = _obs(ctx, "radio", "tocando")
        return bool(cur) is bool(expected), f"radio_tocando={cur} (esperado {expected})"

    if op == "radio_fila_maior_que":
        cur = _obs(ctx, "radio", "fila")
        n = int(expected)
        if cur is None:
            return False, f"radio_fila={cur} (indisponível)"
        return int(cur) > n, f"radio_fila={cur} > {n}"

    if op == "voz_pack":
        cur = _obs(ctx, "voz", "pack")
        return str(cur or "").lower() == str(expected).lower(), f"voz_pack={cur} (esperado {expected})"

    if op == "cpu_maior_que":
        cur = _obs(ctx, "sistema", "cpu_percent")
        n = float(expected)
        if cur is None:
            return False, f"cpu={cur} (indisponível)"
        return float(cur) > n, f"cpu={cur}% > {n}%"

    if op == "metas_ativas_maior_que":
        cur = _obs(ctx, "metas", "ativas")
        n = int(expected)
        if cur is None:
            return False, f"metas_ativas={cur} (indisponível)"
        return int(cur) > n, f"metas_ativas={cur} > {n}"

    if op == "memorias_maior_que":
        cur = _obs(ctx, "memoria", "total")
        n = int(expected)
        if cur is None:
            return False, f"memorias={cur} (indisponível)"
        return int(cur) > n, f"memorias={cur} > {n}"

    if op == "fato_igual":
        fatos = _obs(ctx, "mundo", "fatos")
        if not isinstance(fatos, dict) or not isinstance(expected, dict) or not expected:
            return False, "fato_igual: mundo indisponível ou contrato inválido ({chave: valor})"
        chave, valor = next(iter(expected.items()))
        cur = fatos.get(chave)
        return str(cur) == str(valor), f"fato '{chave}'={cur} (esperado '{valor}')"

    if op == "fato_existe":
        fatos = _obs(ctx, "mundo", "fatos")
        if not isinstance(fatos, dict):
            return False, "fato_existe: mundo indisponível"
        presente = str(expected) in fatos
        return presente, f"fato '{expected}' {'presente' if presente else 'ausente'}"

    if op == "marcador_existe":
        itens = _obs(ctx, "marcadores", "itens")
        if not isinstance(itens, list):
            return False, "marcador_existe: marcadores indisponíveis"
        texto = str(expected).lower()
        hit = any(
            texto in str(i.get("titulo", "")).lower() or texto in str(i.get("url", "")).lower()
            for i in itens
        )
        achou = "encontrado" if hit else "não encontrado"
        return hit, f"marcador contendo '{expected}' {achou} em {len(itens)} marcador(es)"

    if op == "marcadores_maior_que":
        cur = _obs(ctx, "marcadores", "total")
        n = int(expected)
        if cur is None:
            return False, f"marcadores={cur} (indisponível)"
        return int(cur) > n, f"marcadores={cur} > {n}"

    if op == "timer_rodando":
        cur = _obs(ctx, "timetrack", "rodando")
        if cur is None:
            return False, "timer_rodando: timetrack indisponível"
        return bool(cur) is bool(expected), f"timer_rodando={cur} (esperado {expected})"

    if op == "timer_label":
        label = _obs(ctx, "timetrack", "label")
        if label is None:
            return False, "timer_label: nenhum timer aberto"
        return str(label).lower() == str(expected).lower(), f"timer='{label}' (esperado '{expected}')"

    if op == "memoria_tem":
        recentes = _obs(ctx, "memoria", "recentes")
        if not isinstance(recentes, list):
            return False, "memoria_tem: memórias indisponíveis"
        texto = str(expected).lower()
        hit = any(
            texto in str(m.get("titulo", "")).lower() or texto in str(m.get("conteudo", "")).lower()
            for m in recentes
        )
        achou = "encontrada" if hit else "não encontrada"
        return hit, f"memória contendo '{expected}' {achou} em {len(recentes)} recentes"

    return False, f"{op}: operador não implementado"


def eval_conditions(rule: Rule, ctx: dict) -> list[dict]:
    """Avalia todas as condições da regra — todas precisam passar (AND)."""
    details: list[dict] = []
    for op, expected in rule.when.items():
        passed, detail = _eval_one(op, expected, ctx)
        details.append({
            "condicao": op,
            "esperado": expected,
            "passou": passed,
            "detalhe": detail,
        })
    return details


def evaluate(rules: list[Rule], ctx: dict) -> dict:
    """Avalia as regras contra o contexto. Devolve decisões + trilha completa:
    cada regra avaliada tem o detalhe condição por condição — o porquê."""
    ordered = sorted(rules, key=lambda r: (r.priority, r.id), reverse=True)
    trail: list[dict] = []
    decisions: list[dict] = []
    for rule in ordered:
        details = eval_conditions(rule, ctx)
        fired = all(d["passou"] for d in details)
        trail.append({
            "regra": rule.id,
            "descricao": rule.description,
            "disparou": fired,
            "auto": rule.auto,
            "condicoes": details,
        })
        if fired:
            decisions.append({
                "regra": rule.id,
                "descricao": rule.description,
                "prioridade": rule.priority,
                "auto": rule.auto,
                "acoes": rule.actions(),
            })
    return {"decisions": decisions, "trail": trail}
