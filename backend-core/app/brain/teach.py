"""
Teach — turn your own history into training data.

This is how Sexta-Feira stops being a generic model and becomes *yours*:
we export your real conversations and curated memories into a chat-format
JSONL dataset that a LoRA/QLoRA fine-tune consumes. Everything is read from
YOUR local database; nothing is uploaded anywhere.

The actual training runs offline via scripts/finetune_lora.py (on a machine
with a GPU). The resulting adapter is merged into a local model that you then
serve through Ollama — so the whole loop stays on hardware you control.
"""
from __future__ import annotations

import json
from typing import Dict, Iterator, List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Conversation, Memory


def build_dataset(db: Session, owner_id: str) -> List[Dict]:
    """
    Produce a list of chat samples:
        {"messages": [{"role": "system"|"user"|"assistant", "content": ...}]}

    Sources:
      * every conversation turn-pair (owner -> assistant)
      * curated memories, framed as things "you" taught the assistant
    """
    samples: List[Dict] = []
    system = settings.brain_persona

    # 1) Real dialogue: each (owner, assistant) pair becomes a supervised sample.
    convs = db.query(Conversation).filter(Conversation.owner_id == owner_id).all()
    for conv in convs:
        history: List[Dict] = [{"role": "system", "content": system}]
        pending_user = None
        for msg in conv.messages:
            if msg.role == "owner":
                pending_user = msg.content
            elif msg.role == "assistant" and pending_user is not None:
                samples.append({
                    "messages": history
                    + [
                        {"role": "user", "content": pending_user},
                        {"role": "assistant", "content": msg.content},
                    ]
                })
                history = history + [
                    {"role": "user", "content": pending_user},
                    {"role": "assistant", "content": msg.content},
                ]
                pending_user = None

    # 2) Memories: reinforce durable facts as Q/A.
    memories = db.query(Memory).filter(Memory.owner_id == owner_id).all()
    for m in memories:
        samples.append({
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": "O que você sabe sobre mim que é relevante aqui?"},
                {"role": "assistant", "content": m.content},
            ]
        })
    return samples


def to_jsonl(samples: List[Dict]) -> Iterator[str]:
    for s in samples:
        yield json.dumps(s, ensure_ascii=False)
