"""
DecisionEngine — "escolha entre alternativas sob restrições" (North Star).

Deterministic and auditable: given options with normalized criteria and a policy
(weights), it scores each option, picks the best, and can explain WHY. Its
headline use is `decide_next_goal` — what should the owner focus on now? — which
draws on the Planning Engine (the goals), the World Model (the owner's current
state, e.g. inferred energy) and records the decision + emits an event.

The LLM never decides here; it can *ask* the engine (a tool) and get a scored,
explainable answer. This keeps the Kernel independent of the model.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import Decision

_HORIZON_DAYS = 14.0
_LOW_ENERGY_WORDS = ("baixa", "baixo", "cansad", "exaust", "low", "tired")

_DEFAULT_WEIGHTS = {"priority": 0.5, "urgency": 0.3, "momentum": 0.2}
_LOW_ENERGY_WEIGHTS = {"priority": 0.35, "urgency": 0.25, "momentum": 0.4}

_FACTOR_LABEL = {
    "priority": "prioridade alta",
    "urgency": "prazo próximo",
    "momentum": "já em andamento",
}


def _clamp(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


class DecisionEngine:
    def __init__(self, planning=None, world=None, events=None) -> None:
        self.planning = planning  # PlanningEngine | None
        self.world = world        # WorldModel | None
        self.events = events      # EventBus | None

    # ---------- generic scoring primitive (pure, deterministic) ----------

    @staticmethod
    def score_options(options: list[dict], weights: dict[str, float]) -> list[dict]:
        """Score each option by a weighted sum of its normalized criteria.

        Each option: {"id","label","criteria": {name: 0..1}}. Returns the same
        options with a "score", sorted best-first; ties break by label for
        determinism.
        """
        scored: list[dict] = []
        for o in options:
            crit = o.get("criteria", {})
            score = round(sum(w * _clamp(crit.get(k, 0.0)) for k, w in weights.items()), 4)
            scored.append({**o, "score": score})
        return sorted(scored, key=lambda x: (-x["score"], str(x.get("label", ""))))

    # ---------- headline decision: what to focus on next ----------

    def rank_goals(
        self, db: Session, owner_id: str,
    ) -> tuple[list[dict] | None, str | None, dict[str, float] | None]:
        """Ranks choosable goals (scored, best-first) WITHOUT persisting.

        Pure evaluation, the same the headline decision uses: given the owner's
        current state (World Model), pick the policy weights and score every
        pending/active goal. Returns (scored, policy_name, weights) or
        (None, None, None) when there is nothing choosable or planning is off.
        The nucleus calls this to merge goals with the rule engine in one cycle;
        decide_next_goal persists the top one.
        """
        if not self.planning:
            return None, None, None
        candidates = [
            g for g in self.planning.list_goals(db, owner_id)
            if g.status in ("pending", "active")   # blocked/done/cancelled are not choosable
        ]
        if not candidates:
            return None, None, None

        policy_name, weights = self._policy(db, owner_id)
        options = [
            {
                "id": g.id, "label": g.title,
                "criteria": {
                    "priority": _clamp(g.priority / 5.0),
                    "urgency": self._urgency(g.due_at),
                    "momentum": _clamp(g.progress),
                },
            }
            for g in candidates
        ]
        return self.score_options(options, weights), policy_name, weights

    async def record(
        self,
        db: Session,
        owner_id: str,
        *,
        question: str,
        policy: str,
        chosen_id: str | None,
        chosen_label: str | None,
        rationale: str,
        options: list | dict,
        fact_key: str | None = None,
    ) -> Decision:
        """Persists one decision + publishes the event + (opcional) atualiza um
        fato do mundo. O caminho único de registro — o núcleo usa para
        question="nucleo", o decide_next_goal para "next_goal" com o fato
        foco_decidido."""
        decision = Decision(
            id=str(uuid.uuid4()), owner_id=owner_id, question=question, policy=policy,
            chosen_id=chosen_id, chosen_label=chosen_label, rationale=rationale,
            options=json.dumps(options, ensure_ascii=False),
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        if self.events:
            await self.events.publish(
                db, owner_id, "decisao.tomada",
                {"question": question, "chosen": chosen_label, "policy": policy},
                source="decision",
            )
        if self.world and fact_key and chosen_label:
            self.world.set_fact(
                db, owner_id, fact_key, chosen_label,
                category="goals", source="decision",
            )
        return decision

    async def decide_next_goal(self, db: Session, owner_id: str) -> Decision | None:
        scored, policy_name, weights = self.rank_goals(db, owner_id)
        if not scored:
            return None
        best = scored[0]
        return await self.record(
            db, owner_id,
            question="next_goal", policy=policy_name or "default",
            chosen_id=best["id"], chosen_label=best["label"],
            rationale=self._rationale(best, weights or {}),
            options=scored,
            fact_key="foco_decidido",
        )

    # ---------- policy + criteria ----------

    def _policy(self, db: Session, owner_id: str) -> tuple[str, dict[str, float]]:
        """Pick weights from the owner's current state (World Model)."""
        if self.world and self._low_energy(db, owner_id):
            return "low_energy", _LOW_ENERGY_WEIGHTS
        return "default", _DEFAULT_WEIGHTS

    def _low_energy(self, db: Session, owner_id: str) -> bool:
        for key in ("energia", "humor", "estado_usuario"):
            fact = self.world.get_fact(db, owner_id, key)
            if fact and any(w in fact.value.lower() for w in _LOW_ENERGY_WORDS):
                return True
        return False

    @staticmethod
    def _urgency(due_at: datetime | None) -> float:
        if not due_at:
            return 0.3  # no deadline: neutral pull
        now = datetime.now(UTC).replace(tzinfo=None)
        days_left = (due_at - now).total_seconds() / 86400.0
        if days_left < 0:
            return 1.0  # overdue: maximal urgency
        return _clamp(1.0 - days_left / _HORIZON_DAYS)

    @staticmethod
    def _rationale(best: dict, weights: dict[str, float]) -> str:
        crit = best.get("criteria", {})
        contribs = {k: weights.get(k, 0.0) * _clamp(crit.get(k, 0.0)) for k in weights}
        top = max(contribs, key=contribs.get) if contribs else "priority"
        return f"Escolhido por {_FACTOR_LABEL.get(top, top)} (score {best.get('score', 0)})."

    # ---------- audit trail ----------

    def history(self, db: Session, owner_id: str, limit: int = 100) -> list[Decision]:
        return (
            db.query(Decision)
            .filter(Decision.owner_id == owner_id)
            .order_by(Decision.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_decision(self, db: Session, owner_id: str, decision_id: str) -> Decision | None:
        return (
            db.query(Decision)
            .filter(Decision.id == decision_id, Decision.owner_id == owner_id)
            .first()
        )
