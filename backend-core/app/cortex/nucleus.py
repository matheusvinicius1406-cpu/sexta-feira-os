"""
Nucleus — o núcleo decisório: regras + metas + contexto num ciclo único, sem LLM.

Ciclo:
  contexto -> regras (avaliadas com trilha) -> metas (rankeadas pelo
  DecisionEngine, sem persistir) -> escolha final determinística
  -> racional + trilha -> persistida como Decision (question="nucleo").

Duas vozes alimentam a escolha:
  - MUNDO: a regra de maior prioridade que disparou contra o snapshot.
  - FOCO:  a meta melhor rankeada (prioridade + urgência + momentum, com a
           política default/low_energy do World Model).

Regra vence quando tem prioridade >= limiar (sinal forte do mundo); senão o
foco; senão "nenhuma". O racional diz qual voz venceu e por quê — a trilha
completa (condições das regras, score das metas) fica anexada.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.cortex.context import build_context
from app.cortex.rules import evaluate, load_rules

logger = logging.getLogger("sexta-feira.cortex.nucleus")

# Regra com prioridade >= limiar é sinal forte do mundo e vence o foco.
_RULE_THRESHOLD = 20


async def decidir(db: Session, owner_id: str, decision, contexto: dict | None = None) -> dict:
    """Roda o ciclo completo e devolve o veredito com a trilha. `decision` é o
    DecisionEngine do kernel (com planning/world/events injetados). `contexto`
    permite simular o mundo (testes e demonstração); omitido, o kernel monta
    o snapshot real."""
    ctx = contexto if contexto is not None else await build_context(db, owner_id)
    rules = load_rules()
    regras = evaluate(rules, ctx)

    fired = regras["decisions"]
    top_rule = max(fired, key=lambda d: d["prioridade"]) if fired else None

    scored, policy_name, weights = decision.rank_goals(db, owner_id)
    top_goal = scored[0] if scored else None
    foco = (
        {"id": top_goal["id"], "label": top_goal["label"], "score": top_goal.get("score")}
        if top_goal else None
    )

    # ── fusão determinística ──────────────────────────────
    if top_rule and top_rule["prioridade"] >= _RULE_THRESHOLD:
        escolha = {
            "tipo": "regra",
            "alvo": top_rule["regra"],
            "descricao": top_rule["descricao"],
            "acao": top_rule["acoes"][0] if top_rule["acoes"] else None,
        }
        racional = (
            f"Regra '{top_rule['regra']}' (prioridade {top_rule['prioridade']}) disparou "
            "contra o mundo atual — sinal forte do mundo vence o foco."
        )
        policy = "regras_primeiro"
    elif top_goal:
        escolha = {
            "tipo": "foco",
            "alvo": top_goal["id"],
            "descricao": top_goal["label"],
            "score": top_goal.get("score"),
        }
        racional = decision._rationale(top_goal, weights or {})  # noqa: SLF001 — engine interno, estável
        policy = policy_name or "default"
    else:
        escolha = {
            "tipo": "nenhuma",
            "alvo": None,
            "descricao": "Nada exige decisão agora.",
            "acao": None,
        }
        racional = "Nenhuma regra forte disparou e não há meta elegível — nada exige decisão agora."
        policy = "nenhuma"

    # O que foi considerado — regras disparadas + top 3 metas ranqueadas.
    considered = [
        {"tipo": "regra", "id": d["regra"], "prioridade": d["prioridade"]}
        for d in fired
    ]
    considered += [
        {"tipo": "meta", "id": o["id"], "label": o["label"], "score": o.get("score")}
        for o in (scored or [])[:3]
    ]

    recorded = await decision.record(
        db, owner_id,
        question="nucleo", policy=policy,
        chosen_id=escolha["alvo"], chosen_label=escolha["descricao"],
        rationale=racional, options=considered,
        fact_key="foco_decidido" if escolha["tipo"] == "foco" else None,
    )

    return {
        "momento": datetime.now().isoformat(timespec="seconds"),
        "decisao_id": recorded.id,
        "contexto": ctx,
        "regras": {
            "total": len(regras["trail"]),
            "dispararam": len(fired),
            "decisions": fired,
            "trail": regras["trail"],
        },
        "foco": foco,
        "escolha": {**escolha, "rationale": racional, "policy": policy},
    }
