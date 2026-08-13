"""
CognitivePulse — the kernel's own initiative ("agente próprio").

The kernel is an agent, not only a chat endpoint. On an interval (or on
demand) the Pulse wakes, looks at the present (World Model), the goals
(Planning), the lessons (Learning) and the pending proposals, judges whether
anything is worth doing RIGHT NOW, and then:

  * DOES it, when the action is read-only or reversible (safe toolset), or
  * PROPOSES it to the owner, when the action would change the world
    ("age com confirmação") — the owner approves or rejects via the API, and
    the SAME tool then runs through the SAME ToolKit, so there is one dispatch
    path and one audit trail.

The cycle mirrors the Cognitive Kernel loop (docs/jarvis/architecture/
COGNITIVE_KERNEL.md), executed as a background heartbeat instead of only when
the owner speaks:

    contexto → julgar → decidir → agir ou propor → registrar → aprender

Guarantees:
  * No tool outside the pulse's own tables is ever dispatched.
  * World-changing tools never run without an approved proposal.
  * A failing tick never breaks the loop nor the kernel (best-effort).
  * Every cycle that did something is announced as a `pulse.ciclo` event and
    reflected in the kernel's journal — the kernel keeps a diary.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import PulseProposal

logger = logging.getLogger("sexta-feira.pulse")

# Tools the pulse may EXECUTE by itself: read-only or reversible, no
# real-world effect, cheap, and safe for a small model to call on its own.
_SAFE_TOOLS = {
    "recall",
    "list_goals",
    "sprint_board",
    "daily_briefing",
    "decide_next",
    "list_automations",
    "automation_history",
    "recall_lessons",
    "list_capabilities",
    "remember",
    "remember_context",
    "remember_about_me",
    "record_learning",
    "web_search",
    "fetch_page",
}

# Tools that CHANGE the world: the pulse may only PROPOSE these; the owner's
# approval (an approved PulseProposal) is what lets them run.
_WORLD_TOOLS = {
    "run_automation",
    "device_action",
    "schedule_reminder",
    "schedule_action",
    "call_api",
    "create_goal",
    "decompose_goal",
    "complete_goal",
    "delegate",
    "consult_director",
    "play_music",
}

_ALLOWED_TOOLS = _SAFE_TOOLS | _WORLD_TOOLS

# How old a pending proposal gets before it is quietly expired.
_PROPOSAL_TTL = timedelta(days=7)
# Goals that close within this horizon are worth noticing in the scan.
_DUE_HORIZON = timedelta(hours=48)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_judgment(raw: str) -> dict | None:
    """Extract the model's JSON answer tolerantly (small models mangle JSON).

    Accepts a bare JSON object, or one wrapped in prose/markdown fences. Any
    failure means "no judgment" — the pulse skips the cycle instead of acting
    on garbage.
    """
    if not raw:
        return None
    for candidate in _JSON_BLOCK.findall(raw):
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


class CognitivePulse:
    def __init__(
        self, brain, toolkit, world=None, planning=None, decision=None,
        learning=None, events=None, journal=None,
    ):
        self.brain = brain            # LocalBrain — the reasoning mechanism
        self.toolkit = toolkit        # ToolKit — one dispatch path with the chat
        self.world = world            # WorldModel | None
        self.planning = planning      # PlanningEngine | None
        self.decision = decision      # DecisionEngine | None
        self.learning = learning      # LearningEngine | None
        self.events = events          # EventBus | None
        self.journal = journal        # JournalService | None — the kernel's diary
        # (tool, canonical-args) -> unix ts of last execution, so the pulse
        # does not repeat the same safe action every single cycle.
        self._ran: dict[str, float] = {}
        self.last_report: dict | None = None
        # Fingerprint of the last digest actually sent to _judge, and whether
        # that judgment came back "nothing to do" — see _should_judge.
        self._last_digest_hash: str | None = None
        self._last_judgment_was_nothing = False

    # ---------- one cycle ----------

    async def tick(self, db: Session, owner_id: str, reason: str = "heartbeat") -> dict:
        """One autonomous cycle: notice, judge, act or propose, record.

        Returns a report dict — the unit tests drive this method directly.
        """
        report = {"reason": reason, "noticed": [], "executed": [], "proposed": [], "skipped": []}

        # 1. Deterministic scan — things the kernel notices without thinking.
        notes = self._scan(db, owner_id)
        report["noticed"] = notes

        # 2. Judgment — one cheap LLM call about what is worth doing NOW,
        # skipped when the state is identical to the last digest judged AND
        # that judgment found nothing to do — see _should_judge.
        judgment = None
        if self.brain is not None:
            try:
                digest = self._digest(db, owner_id, notes)
                digest_hash = hashlib.sha256(digest.encode("utf-8")).hexdigest()
                if self._should_judge(digest_hash):
                    judgment = await self._judge(db, owner_id, digest)
                    self._last_digest_hash = digest_hash
                    self._last_judgment_was_nothing = (
                        isinstance(judgment, dict) and bool(judgment.get("nothing"))
                    )
                else:
                    report["skipped"].append(
                        "julgamento pulado: mesmo estado do último 'nada a fazer'"
                    )
            except Exception as e:  # noqa: BLE001 — brain down must not kill the tick
                logger.debug("pulse judgment unavailable: %s", e)
                report["skipped"].append(f"julgamento indisponível: {e}")

        # 3. Act or propose.
        if judgment and not judgment.get("nothing"):
            tool = judgment.get("tool")
            args = judgment.get("args") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            title = str(judgment.get("title") or f"agir: {tool}").strip()
            reason_line = str(judgment.get("reason") or "o pulse julgou oportuno").strip()
            await self._handle_judgment(db, owner_id, tool, args, title, reason_line, report)

        # 4. Record — journal + event + learning, only when something happened.
        diary = list(notes)
        if report["executed"]:
            diary.append("agi: " + "; ".join(f"{e['tool']}" for e in report["executed"]))
        if report["proposed"]:
            diary.append("propus: " + "; ".join(f"{p['title']}" for p in report["proposed"]))
        if diary:
            await self._record_cycle(db, owner_id, reason, report, diary)

        self.last_report = report
        return report

    async def _handle_judgment(
        self, db: Session, owner_id: str, tool: str,
        args: dict, title: str, reason_line: str, report: dict,
    ) -> None:
        if not self.toolkit:
            report["skipped"].append("toolkit indisponível")
            return
        if not isinstance(tool, str) or tool not in _ALLOWED_TOOLS:
            report["skipped"].append(f"ferramenta fora da lista do agente: {tool}")
            return

        key = f"{tool}:{json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)}"

        if tool in _SAFE_TOOLS:
            if self._cooldown_hit(key):
                report["skipped"].append(f"{tool} já feito há pouco")
                return
            result = await self.toolkit.dispatch(tool, args, db, owner_id)
            self._ran[key] = time.time()
            report["executed"].append({"tool": tool, "args": args, "result": result[:300]})
            logger.info("pulse agiu: %s -> %s", tool, result[:80])
            return

        # World-changing: propose, never execute.
        if self._pending_exists(db, owner_id, key):
            report["skipped"].append(f"{tool} já proposto (aguardando decisão)")
            return
        p = self.propose(db, owner_id, tool, args, title, reason_line)
        report["proposed"].append({"id": p.id, "tool": tool, "title": p.title})
        logger.info("pulse propôs: %s (%s)", p.title, tool)

    # ---------- deterministic scan ----------

    def _scan(self, db: Session, owner_id: str) -> list[str]:
        """Notice things without an LLM: due goals, recurring difficulties,
        stale proposals. Returns human-readable lines for the journal."""
        notes: list[str] = []
        naive_now = _now().replace(tzinfo=None)
        if self.planning:
            for g in self.planning.list_goals(db, owner_id):
                if g.status not in ("pending", "active") or not g.due_at:
                    continue
                remaining = g.due_at - naive_now
                if remaining < timedelta(0):
                    notes.append(f"objetivo '{g.title}' está atrasado")
                elif remaining <= _DUE_HORIZON:
                    notes.append(f"objetivo '{g.title}' vence em {max(1, int(remaining.total_seconds() // 3600))}h")
        if self.learning:
            low = [
                lesson for lesson in self.learning.lessons(db, owner_id, limit=10)
                if lesson.quality is not None and lesson.quality < 0.4
            ]
            for lesson in low[:1]:
                notes.append(f"dificuldade recorrente: {lesson.tag or lesson.context[:60]}")
        self._expire_stale(db, owner_id)
        return notes[:5]

    def _expire_stale(self, db: Session, owner_id: str) -> None:
        cutoff = _now() - _PROPOSAL_TTL
        stale = (
            db.query(PulseProposal)
            .filter(
                PulseProposal.owner_id == owner_id,
                PulseProposal.status == "pending",
                PulseProposal.created_at < cutoff,
            )
            .all()
        )
        for p in stale:
            p.status = "expired"
            p.decided_at = _now()
        if stale:
            db.commit()

    def _pending_exists(self, db: Session, owner_id: str, key: str) -> bool:
        rows = (
            db.query(PulseProposal)
            .filter(
                PulseProposal.owner_id == owner_id,
                PulseProposal.status == "pending",
                PulseProposal.tool.isnot(None),
            )
            .all()
        )
        for p in rows:
            if f"{p.tool}:{p.tool_args or '{}'}" == key:
                return True
        return False

    def _cooldown_hit(self, key: str) -> bool:
        last = self._ran.get(key)
        if last is None:
            return False
        return (time.time() - last) < settings.agent_pulse_cooldown_seconds

    def _should_judge(self, digest_hash: str) -> bool:
        """False only when nothing has moved since the last judged digest
        found nothing worth doing.

        A digest that has never been judged, or was last judged with an
        actual tool/proposal, always gets judged again — this only collapses
        the case where an idle owner would otherwise pay for the SAME
        "nothing to do" answer every single tick. AGENT_PULSE_JUDGE_WHEN_IDLE
        restores the old always-judge behaviour for anyone who wants the LLM
        checked on every heartbeat regardless.
        """
        if settings.agent_pulse_judge_when_idle:
            return True
        return not (digest_hash == self._last_digest_hash and self._last_judgment_was_nothing)

    # ---------- judgment ----------

    def _digest(self, db: Session, owner_id: str, notes: list[str]) -> str:
        parts: list[str] = []
        if notes:
            parts.append("O que o kernel já notou:\n" + "\n".join(f"- {n}" for n in notes))
        if self.world:
            digest = self.world.context_digest(db, owner_id, max_world=8, max_user=6)
            if digest:
                parts.append(digest)
        if self.planning:
            goals = [
                g for g in self.planning.list_goals(db, owner_id)
                if g.status in ("pending", "active")
            ][:5]
            if goals:
                lines = []
                for g in goals:
                    due = g.due_at.strftime("%d/%m") if g.due_at else "sem prazo"
                    lines.append(f"- [{g.status}] {g.title} ({int(g.progress * 100)}%, {due})")
                parts.append("Objetivos abertos:\n" + "\n".join(lines))
        if self.learning:
            lessons = self.learning.lessons(db, owner_id, limit=3)
            if lessons:
                parts.append(
                    "Aprendizados recentes:\n"
                    + "\n".join(f"- {lesson.lesson or lesson.context[:80]}" for lesson in lessons)
                )
        pending = self.list_proposals(db, owner_id, status="pending")
        if pending:
            parts.append(f"Propostas aguardando o dono: {len(pending)} (não repita a mesma ação)")
        return "\n\n".join(parts) or "Nada de novo no estado."

    async def _judge(self, db: Session, owner_id: str, digest: str) -> dict | None:
        system = (
            "Você é Sexta-Feira em modo agente: o kernel pensa sozinho em segundo plano, "
            "sem ninguém pedir. Dado o estado abaixo, decida se há UMA ação útil a "
            "executar agora — algo que valha a pena fazer por conta própria. "
            "Responda APENAS com JSON válido, sem texto fora dele:\n"
            '{"tool": "<nome>", "args": {...}, "title": "<título curto>", '
            '"reason": "<por que agora>"}\n'
            "Se nada valer a pena, responda {\"nothing\": true}.\n"
            "Ferramentas que você pode executar: "
            + ", ".join(sorted(_SAFE_TOOLS))
            + ".\n"
            "Ferramentas que mudam o mundo (só pode PROPOR): "
            + ", ".join(sorted(_WORLD_TOOLS))
            + ".\n"
            "Não invente ferramentas fora dessas listas."
        )
        raw = await self.brain.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": digest}],
            temperature=0.2,
            max_tokens=250,
        )
        return _parse_judgment(raw)

    # ---------- proposals (the confirmation gate) ----------

    def propose(
        self, db: Session, owner_id: str, tool: str, args: dict,
        title: str, reason: str | None = None,
    ) -> PulseProposal:
        p = PulseProposal(
            id=str(uuid.uuid4()), owner_id=owner_id, kind="action", status="pending",
            title=title[:200], reason=reason,
            tool=tool,
            # sort_keys=True: the dedupe key (tool + canonical args) is built the
            # same way, so a repeated proposal is recognized and not filed twice.
            tool_args=json.dumps(args, sort_keys=True, ensure_ascii=False) if args else None,
            source="pulse",
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p

    def get_proposal(self, db: Session, owner_id: str, proposal_id: str) -> PulseProposal | None:
        return (
            db.query(PulseProposal)
            .filter(PulseProposal.id == proposal_id, PulseProposal.owner_id == owner_id)
            .first()
        )

    def list_proposals(
        self, db: Session, owner_id: str, status: str | None = None, limit: int = 50,
    ) -> list[PulseProposal]:
        q = db.query(PulseProposal).filter(PulseProposal.owner_id == owner_id)
        if status:
            q = q.filter(PulseProposal.status == status)
        return q.order_by(PulseProposal.created_at.desc()).limit(limit).all()

    async def execute_proposal(
        self, db: Session, owner_id: str, proposal_id: str,
    ) -> PulseProposal:
        """Approve + run. The owner said yes; the SAME tool runs through the
        same ToolKit the chat uses — one dispatch path, one audit trail."""
        p = self.get_proposal(db, owner_id, proposal_id)
        if not p:
            raise ValueError("proposal not found")
        if p.status != "pending":
            raise ValueError(f"proposal is {p.status}, not pending")
        p.status = "approved"
        p.decided_at = _now()
        db.commit()

        if not p.tool:
            p.status = "executed"
            p.result = "informativo — sem ação a executar"
            p.executed_at = _now()
            db.commit()
            await self._emit_proposal(db, owner_id, p, "pulse.proposta.executada")
            return p

        if self.toolkit is None:
            p.status = "failed"
            p.error = "toolkit indisponível"
            p.executed_at = _now()
            db.commit()
            return p

        try:
            args = json.loads(p.tool_args) if p.tool_args else {}
            result = await self.toolkit.dispatch(p.tool, args, db, owner_id)
            p.result = result[:1000]
            p.error = None
            p.status = "executed"
        except Exception as e:  # noqa: BLE001 — surface the failure on the proposal
            p.error = str(e)[:500]
            p.status = "failed"
        p.executed_at = _now()
        db.commit()
        await self._emit_proposal(db, owner_id, p, "pulse.proposta.executada")
        return p

    def reject_proposal(
        self, db: Session, owner_id: str, proposal_id: str,
    ) -> PulseProposal:
        p = self.get_proposal(db, owner_id, proposal_id)
        if not p:
            raise ValueError("proposal not found")
        if p.status != "pending":
            raise ValueError(f"proposal is {p.status}, not pending")
        p.status = "rejected"
        p.decided_at = _now()
        db.commit()
        return p

    # ---------- recording ----------

    async def _record_cycle(
        self, db: Session, owner_id: str, reason: str, report: dict, diary: list[str],
    ) -> None:
        if self.events:
            await self.events.publish(
                db, owner_id, "pulse.ciclo",
                {
                    "reason": reason,
                    "executed": [e["tool"] for e in report["executed"]],
                    "proposed": [p["tool"] for p in report["proposed"]],
                },
                source="pulse",
            )
        if self.journal:
            try:
                # distil=False: this line is the AGENT's log of what it did,
                # not a durable fact about the owner. Distilling it anyway used
                # to spend a full extraction (see JournalService.add) on every
                # tick that merely noticed something, not just the ones that
                # acted — the second, uncosted cascade behind a "cheap" pulse.
                await self.journal.add(
                    db, owner_id, "Pulse — " + " | ".join(diary), distil=False,
                )
            except Exception as e:  # noqa: BLE001 — the diary must not break the cycle
                logger.debug("pulse diary skipped: %s", e)

    async def _emit_proposal(
        self, db: Session, owner_id: str, p: PulseProposal, etype: str,
    ) -> None:
        if self.events:
            await self.events.publish(
                db, owner_id, etype,
                {"proposal_id": p.id, "tool": p.tool, "status": p.status},
                source="pulse",
            )
