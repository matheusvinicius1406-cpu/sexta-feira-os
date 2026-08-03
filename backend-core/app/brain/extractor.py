"""
MemoryExtractor — distil durable, TYPED facts from a conversation turn.

Upgrade over the old single-fact auto-learn: one exchange can yield SEVERAL
memories, each classified and routed to the right place:
  * fact / preference / person / routine / note  -> graph Memory (auto-links)
  * a stable owner trait (with `chave_perfil`)   -> User Model (upsert by key)

The local brain proposes candidates as JSON; everything around it is
deterministic and defensive: malformed output extracts nothing, kinds are
clamped to a whitelist, at most MAX_FACTS are stored, exact duplicates are
skipped, and a failure never breaks the reply (best-effort, like auto-learn).
Emits `memoria.extraida` so the extraction itself is auditable.

Concept adapted (our own code) from the Apache-2.0 OpenJarvis memory extractor;
see ADR-0007. All inference is local (Ollama) — "só meu".
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.models import Memory

logger = logging.getLogger("sexta-feira.extractor")

MAX_FACTS = 5
_ALLOWED_KINDS = {"fact", "preference", "person", "routine", "note"}

_PROMPT = (
    "Você extrai memórias duráveis sobre o DONO a partir de uma troca de mensagens. "
    "Responda APENAS com um array JSON (sem texto em volta). Cada item: "
    '{"fato": "frase curta e autossuficiente", '
    '"tipo": "fact|preference|person|routine|note", '
    '"importancia": 0.0 a 1.0, '
    '"chave_perfil": "opcional — nome_da_chave se for um traço estável do dono '
    '(ex.: estilo_programacao, meta_principal), senão omita"}. '
    "Extraia só o que vale lembrar por meses (preferências, pessoas, rotinas, metas, "
    "detalhes pessoais). Se não houver nada digno, responda []."
)


def _clamp(x, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return default


def _parse_candidates(raw: str) -> list[dict]:
    """Parse the model's JSON array defensively; garbage in -> nothing out."""
    text = (raw or "").strip()
    # Tolerate markdown fences and prose around the array.
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        fact = str(item.get("fato", "")).strip()
        if len(fact) < 8:
            continue
        kind = str(item.get("tipo", "fact")).strip().lower()
        out.append({
            "content": fact,
            "kind": kind if kind in _ALLOWED_KINDS else "fact",
            "importance": _clamp(item.get("importancia", 0.5)),
            "profile_key": str(item.get("chave_perfil", "")).strip() or None,
        })
    return out[:MAX_FACTS]


class MemoryExtractor:
    def __init__(self, brain, memory, world=None, events=None, on_stored=None):
        self.brain = brain    # LocalBrain
        self.memory = memory  # PersistentMemory
        self.world = world    # WorldModel | None (User Model routing)
        self.events = events  # EventBus | None
        # Called once per fact actually stored, as (content, kind). The kernel
        # uses it to mirror the fact into the Obsidian vault. A callback rather
        # than an import keeps the extractor unaware of where else a fact goes.
        self.on_stored = on_stored

    async def extract(self, db: Session, owner_id: str, user_text: str, reply: str) -> int:
        """Distil and store durable facts from one exchange. Returns how many stored."""
        probe = [
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": f"Usuário: {user_text}\nAssistente: {reply}"},
        ]
        raw = await self.brain.chat(probe, temperature=0.1, max_tokens=400)
        candidates = _parse_candidates(raw)
        stored = 0
        for c in candidates:
            if self._is_duplicate(db, owner_id, c["content"]):
                continue
            await self.memory.remember(
                db, owner_id, c["content"], kind=c["kind"],
                importance=c["importance"], source="auto_learned",
            )
            if c["profile_key"] and self.world:
                self.world.set_attribute(
                    db, owner_id, c["profile_key"], c["content"],
                    category="other", source="extractor", is_inference=True,
                )
            if self.on_stored:
                try:
                    self.on_stored(c["content"], c["kind"])
                except Exception as e:  # noqa: BLE001 — mirroring never breaks learning
                    logger.debug("could not mirror fact outside memory: %s", e)
            stored += 1
        if stored and self.events:
            await self.events.publish(
                db, owner_id, "memoria.extraida", {"count": stored}, source="extractor",
            )
        return stored

    @staticmethod
    def _is_duplicate(db: Session, owner_id: str, content: str) -> bool:
        return (
            db.query(Memory)
            .filter(Memory.owner_id == owner_id, Memory.content == content)
            .first()
        ) is not None
