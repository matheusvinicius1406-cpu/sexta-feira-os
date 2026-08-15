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
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/cortex", tags=["cortex"])


class CortexIntentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


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
