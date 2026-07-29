"""
Evals — the brain measures its own quality (owner-defined checks, local model).

  POST /api/v1/evals/cases    add/update a case (prompt + expected substring)
  GET  /api/v1/evals/cases    list cases
  POST /api/v1/evals/run      run all enabled cases on the local brain
  GET  /api/v1/evals/runs     score history
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.engine import BrainUnavailable
from app.core.di import get_evals
from app.db.database import get_db
from app.evals.service import EvalHarness
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/evals", tags=["evals"])


class CaseRequest(BaseModel):
    name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    expected_contains: str = Field(..., min_length=1)


def _run_out(r) -> dict:
    return {
        "id": r.id, "total": r.total, "passed": r.passed, "score": r.score,
        "results": json.loads(r.results) if r.results else [],
        "created_at": r.created_at,
    }


@router.post("/cases")
def add_case(
    body: CaseRequest,
    owner: Owner = Depends(get_current_owner),
    evals: EvalHarness = Depends(get_evals),
    db: Session = Depends(get_db),
):
    c = evals.add_case(db, owner.id, body.name, body.prompt, body.expected_contains)
    return {"id": c.id, "name": c.name, "prompt": c.prompt,
            "expected_contains": c.expected_contains}


@router.get("/cases")
def list_cases(
    owner: Owner = Depends(get_current_owner),
    evals: EvalHarness = Depends(get_evals),
    db: Session = Depends(get_db),
):
    return [
        {"id": c.id, "name": c.name, "prompt": c.prompt,
         "expected_contains": c.expected_contains, "enabled": c.enabled}
        for c in evals.list_cases(db, owner.id)
    ]


@router.post("/run")
async def run(
    owner: Owner = Depends(get_current_owner),
    evals: EvalHarness = Depends(get_evals),
    db: Session = Depends(get_db),
):
    try:
        r = await evals.run(db, owner.id)
    except BrainUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    if not r:
        return {"run": None, "reason": "Nenhum caso de avaliação cadastrado."}
    return {"run": _run_out(r)}


@router.get("/runs")
def runs(
    limit: int = 30,
    owner: Owner = Depends(get_current_owner),
    evals: EvalHarness = Depends(get_evals),
    db: Session = Depends(get_db),
):
    return [_run_out(r) for r in evals.history(db, owner.id, limit)]
