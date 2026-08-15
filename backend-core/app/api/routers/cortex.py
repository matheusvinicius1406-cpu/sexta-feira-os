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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.cortex import VERBS, parse, run_intent
from app.cortex.context import build_context
from app.cortex.nucleus import decidir, propor_regras
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


def _nucleo_out(d) -> dict:
    import json as _json

    return {
        "id": d.id,
        "question": d.question,
        "policy": d.policy,
        "chosen_id": d.chosen_id,
        "chosen_label": d.chosen_label,
        "rationale": d.rationale,
        "options": _json.loads(d.options) if d.options else [],
        "created_at": d.created_at,
    }


class CortexCicloAgendarRequest(BaseModel):
    """O ciclo autônomo: a cada `intervalo_minutos`, o kernel acorda e o
    núcleo avalia as regras — cada regra disparada vira proposta do agente.
    Idempotente: agendar de novo devolve a mesma tarefa (sem duplicar)."""
    intervalo_minutos: int = Field(default=60, ge=5, le=24 * 60)
    iniciar_em_minutos: float = Field(default=1, ge=0, le=24 * 60)


@router.post("/ciclo/agendar")
async def cortex_ciclo_agendar(
    body: CortexCicloAgendarRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Agenda o ciclo decisório recorrente (kind="cortex"). Idempotente: se já
    existe uma tarefa recorrente pendente do mesmo intervalo, devolve a mesma."""
    from app.brain.tools import _compute_due
    from app.core.di import get_scheduler

    scheduler = get_scheduler()
    recurrence = body.intervalo_minutos * 60
    for t in scheduler.list(db, owner.id):
        if t["kind"] == "cortex" and t["recurrence_seconds"] == recurrence:
            return {"agendado": t, "repetido": True}

    due = _compute_due({"in_minutes": body.iniciar_em_minutos})
    task = scheduler.schedule(
        db, owner.id, kind="cortex", due_at=due,
        text="Ciclo decisório do núcleo (regras → propostas)",
        recurrence_seconds=recurrence,
    )
    return {"agendado": scheduler._to_dict(task), "repetido": False}


@router.get("/ciclo")
async def cortex_ciclo_status(
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Status do ciclo autônomo: a tarefa recorrente agendada, as últimas
    execuções disparadas e as propostas de regra geradas por elas."""
    from app.core.di import get_pulse, get_scheduler

    scheduler = get_scheduler()
    agendado = next(
        (t for t in scheduler.list(db, owner.id) if t["kind"] == "cortex"),
        None,
    )
    historico = [
        t for t in scheduler.list(db, owner.id, include_done=True)
        if t["kind"] == "cortex" and t["status"] == "fired"
    ][-5:]

    pulse = get_pulse()
    propostas = []
    if pulse is not None:
        for p in pulse.list_proposals(db, owner.id, limit=20):
            if p.source == "cortex":
                propostas.append({
                    "id": p.id, "title": p.title, "status": p.status,
                    "created_at": p.created_at,
                })

    return {
        "agendado": agendado,
        "historico": list(reversed(historico)),
        "propostas": propostas,
        "engine": "symbolic",
    }


class CortexDecidirRequest(BaseModel):
    """Contexto simulado opcional — o mesmo contrato de rules/avaliar. Sem ele,
    o núcleo monta o snapshot real do mundo."""
    contexto: dict | None = Field(default=None, max_length=50_000)


@router.post("/decidir")
async def cortex_decidir(
    body: CortexDecidirRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """O núcleo decisório num ciclo único, sem LLM: contexto → regras → metas
    (ranqueadas pelo DecisionEngine) → escolha determinística com racional +
    trilha, persistida em Decision (question="nucleo")."""
    from app.core.di import get_decision

    return await decidir(db, owner.id, get_decision(), contexto=body.contexto)


@router.post("/regras/propor")
async def cortex_regras_propor(
    body: CortexRulesEvaluateRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Regras disparadas viram PROPOSTAS do agente (source="cortex"), com a
    trilha anexada no reason. Aprovar executa pelo toolkit; regras `auto: true`
    executam na hora pelo mesmo rastro."""
    from app.core.di import get_pulse

    pulse = get_pulse()
    if pulse is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Pulse desligado (AGENT_PULSE_ENABLED=false) — regras não podem virar propostas.",
        )
    return await propor_regras(db, owner.id, pulse, contexto=body.contexto)


@router.get("/decidir/ultimo")
async def cortex_decidir_ultimo(
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """A última decisão do núcleo — o "por que decidi" persistido."""
    from app.core.di import get_decision

    history = get_decision().history(db, owner.id, limit=30)
    last = next((d for d in history if d.question == "nucleo"), None)
    return {"decisao": _nucleo_out(last) if last else None}
