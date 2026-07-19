"""
EvalHarness — the second brain measures its own quality.

The owner defines cases (prompt + expected substring); the harness runs them on
the LOCAL model, scores pass/fail deterministically, persists the run, publishes
`avaliacao.executada` and records the score in the Learning Engine — so a drop in
quality becomes a recorded lesson. Useful before/after swapping the local model
(the LLM is substitutable; now we can PROVE a swap didn't regress).

Concept adapted (our own code) from the Apache-2.0 OpenJarvis evals subsystem;
see ADR-0011. No cloud backends — "só meu".
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.models.models import EvalCase, EvalRun

logger = logging.getLogger("sexta-feira.evals")


class EvalHarness:
    def __init__(self, brain, events=None, learning=None):
        self.brain = brain      # LocalBrain
        self.events = events    # EventBus | None
        self.learning = learning  # LearningEngine | None

    # ---------- cases ----------

    def add_case(
        self, db: Session, owner_id: str, name: str, prompt: str, expected_contains: str
    ) -> EvalCase:
        slug = (name or "").strip().lower()
        if not slug or not (prompt or "").strip() or not (expected_contains or "").strip():
            raise ValueError("eval case needs name, prompt and expected_contains")
        case = (
            db.query(EvalCase)
            .filter(EvalCase.owner_id == owner_id, EvalCase.name == slug)
            .first()
        )
        if case:
            case.prompt = prompt
            case.expected_contains = expected_contains
        else:
            case = EvalCase(
                id=str(uuid.uuid4()), owner_id=owner_id, name=slug,
                prompt=prompt, expected_contains=expected_contains,
            )
            db.add(case)
        db.commit()
        db.refresh(case)
        return case

    def list_cases(self, db: Session, owner_id: str) -> list[EvalCase]:
        return (
            db.query(EvalCase)
            .filter(EvalCase.owner_id == owner_id)
            .order_by(EvalCase.name)
            .all()
        )

    # ---------- running ----------

    async def run(self, db: Session, owner_id: str) -> EvalRun | None:
        cases = [c for c in self.list_cases(db, owner_id) if c.enabled]
        if not cases:
            return None
        results = []
        passed = 0
        for case in cases:
            reply = await self.brain.chat(
                [{"role": "user", "content": case.prompt}], temperature=0.0, max_tokens=300
            )
            ok = case.expected_contains.lower() in (reply or "").lower()
            passed += int(ok)
            results.append({"case": case.name, "passed": ok, "reply": (reply or "")[:300]})
        score = round(passed / len(cases), 4)
        run = EvalRun(
            id=str(uuid.uuid4()), owner_id=owner_id, total=len(cases),
            passed=passed, score=score, results=json.dumps(results, ensure_ascii=False),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        if self.events:
            await self.events.publish(
                db, owner_id, "avaliacao.executada",
                {"score": score, "passed": passed, "total": len(cases)}, source="evals",
            )
        if self.learning:
            try:  # a learning hiccup never breaks the run
                await self.learning.record(
                    db, owner_id, f"avaliação do cérebro ({passed}/{len(cases)})",
                    quality=score, tag="eval", ref_id=run.id, source="evals",
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("eval learning skipped: %s", e)
        return run

    def history(self, db: Session, owner_id: str, limit: int = 30) -> list[EvalRun]:
        return (
            db.query(EvalRun)
            .filter(EvalRun.owner_id == owner_id)
            .order_by(EvalRun.created_at.desc())
            .limit(limit)
            .all()
        )
