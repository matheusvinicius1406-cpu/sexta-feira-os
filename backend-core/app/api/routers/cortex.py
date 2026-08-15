"""
Cortex — the hand-built brain exposed over HTTP.

  GET  /api/v1/cortex/verbs        the grammar the cortex knows (honest list)
  POST /api/v1/cortex/intent       fala -> intenção -> ação -> resposta

Nenhum endpoint aqui chama LLM. O caminho é determinístico:

  text -> parse() (gramática declarativa) -> run_intent() (engines reais)
       -> resposta honesta (texto do que aconteceu)

O HUD usa /intent como o "cérebro de comandos": o que a paleta não conhece,
o cortex decide — e a resposta pode vir falada (TTS) ou mostrada.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.cortex import VERBS, parse, run_intent
from app.cortex.context import build_context
from app.cortex.rules import RuleError, evaluate, load_rules
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/cortex", tags=["cortex"])


class CortexIntentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class CortexRulesEvaluateRequest(BaseModel):
    """Permite avaliar num contexto simulado (testes e demonstração). Se
    omitido, o kernel monta o snapshot real do mundo."""
    contexto: dict | None = Field(default=None, max_length=50_000)


@router.get("/verbs")
async def cortex_verbs(
    owner: Owner = Depends(get_current_owner),
):
    """Lista o que o cortex sabe entender — o 'não entendi' honesto e o
    autocompletar do HUD usam esta lista."""
    return {
        "verbs": [
            {"name": v.name, "description": v.description}
            for v in VERBS
        ],
        "count": len(VERBS),
        "engine": "symbolic",
    }


@router.post("/intent")
async def cortex_intent(
    body: CortexIntentRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Fala -> intenção -> ação. `understood=false` significa que a gramática
    não reconheceu — o HUD mostra os verbos conhecidos em vez de inventar."""
    it = parse(VERBS, body.text)
    if it is None:
        return {
            "understood": False,
            "verb": None,
            "target": None,
            "params": {},
            "trace": [],
            "response": None,
            "known": [{"name": v.name, "description": v.description} for v in VERBS],
        }

    response = await run_intent(db, owner.id, it)
    return {
        "understood": True,
        "verb": it.verb,
        "target": it.target,
        "params": it.params,
        "trace": it.trace,
        "response": response,
        "raw": it.raw,
    }


@router.get("/rules")
async def cortex_rules(
    owner: Owner = Depends(get_current_owner),
):
    """Lista as regras declarativas carregadas — o que o cortex considera
    antes de decidir."""
    rules = load_rules()
    return {
        "regras": [
            {
                "id": r.id,
                "descricao": r.description,
                "prioridade": r.priority,
                "auto": r.auto,
                "condicoes": r.when,
                "acoes": r.actions(),
                "arquivo": r.source,
            }
            for r in rules
        ],
        "count": len(rules),
    }


@router.post("/rules/avaliar")
async def cortex_rules_evaluate(
    body: CortexRulesEvaluateRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Avalia as regras contra o snapshot do mundo (ou um contexto simulado)
    e devolve as decisões com a trilha condição por condição. Decisões com
    `auto: true` executam os intents nas engines reais; as demais propõem."""
    try:
        rules = load_rules()
    except RuleError as e:
        return {"erro": str(e), "decisions": [], "trail": []}

    ctx = body.contexto if body.contexto is not None else await build_context(db, owner.id)
    result = evaluate(rules, ctx)

    # Executa só o que a regra declarou `auto: true` — a autonomia é opt-in
    # por regra, escrita no arquivo versionado, nunca no pedido.
    for decision in result["decisions"]:
        if not decision["auto"]:
            continue
        for acao in decision["acoes"]:
            if acao["tipo"] != "intent":
                continue
            verb = acao["valor"].get("verb", "")
            target = acao["valor"].get("target")
            texto = f"{verb} {target}".strip()
            it = parse(VERBS, texto)
            if it is not None:
                decision.setdefault("executado", []).append(
                    {"verb": it.verb, "response": await run_intent(db, owner.id, it)}
                )

    return {"decisions": result["decisions"], "trail": result["trail"], "contexto": ctx}
