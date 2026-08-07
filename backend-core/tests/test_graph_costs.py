"""
Graph edge costs — the LLM call this repo used to spend on a label nobody reads.

`_label_relation` used to run on EVERY auto-linked edge (up to graph_autolink_k
per remembered fact) unconditionally — one full local inference per edge, on
top of whatever inference produced the reply itself. But `recall_graph` ranks
purely on similarity*decay*weight (see memory.py::recall_graph), and the
prompt only ever shows a memory's CONTENT (cognition.py::_build_messages) —
the label is written and never read back. Worse, `relation` is part of
link()'s idempotency key, so a non-deterministic label on a re-labeled pair
files a SECOND edge instead of updating the first.

These tests hold that `graph_relation_labels=False` (the new default) skips
the LLM call entirely — not just discards its result — and that turning it
back on restores labeling for owners who want it in the graph view.
"""
from __future__ import annotations

import asyncio

import pytest

from app.brain.memory import PersistentMemory
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.models import Owner


class SpyBrain:
    """Fake LocalBrain: records whether `.chat()` was ever asked to label an
    edge, and returns a fixed embedding so every memory is its own semantic
    neighbour — auto-link always has a candidate to (maybe) label."""

    def __init__(self) -> None:
        self.chat_calls = 0

    async def embed(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def chat(self, messages, temperature=None, max_tokens=None) -> str:
        self.chat_calls += 1
        return "rótulo-fake"


@pytest.fixture
def owner_id(client):
    """Depends on `client` (session-scoped) so the owner exists even when this
    file runs standalone — the owner row is created by app startup, not by
    the migrations conftest runs eagerly."""
    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        assert owner is not None, "seed owner missing — did app startup run?"
        return owner.id
    finally:
        db.close()


def test_default_never_calls_the_brain_to_label_an_edge(owner_id, monkeypatch):
    monkeypatch.setattr(settings, "graph_relation_labels", False)
    brain = SpyBrain()
    memory = PersistentMemory(brain)
    db = SessionLocal()
    try:
        asyncio.run(memory.remember(db, owner_id, "Matheus trabalha na Acme", auto_link=True))
        asyncio.run(memory.remember(db, owner_id, "Matheus gosta de café forte", auto_link=True))
    finally:
        db.close()

    assert brain.chat_calls == 0, "labeling ran despite graph_relation_labels=False"


def test_default_still_links_edges_just_unlabeled(owner_id, monkeypatch):
    monkeypatch.setattr(settings, "graph_relation_labels", False)
    brain = SpyBrain()
    memory = PersistentMemory(brain)
    db = SessionLocal()
    try:
        first = asyncio.run(memory.remember(db, owner_id, "Matheus trabalha na Acme", auto_link=True))
        asyncio.run(memory.remember(db, owner_id, "Matheus trabalha na Acme todo dia", auto_link=True))
        neighbours = memory.neighbours(db, owner_id, first.id)
    finally:
        db.close()

    semantic = [
        e for e in neighbours["links"] + neighbours["backlinks"]
        if e["origin"] == "semantic"
    ]
    assert semantic, "turning labeling off must not turn linking off"
    assert all(e["relation"] == "related" for e in semantic)


def test_opting_back_in_restores_labeling(owner_id, monkeypatch):
    monkeypatch.setattr(settings, "graph_relation_labels", True)
    brain = SpyBrain()
    memory = PersistentMemory(brain)
    db = SessionLocal()
    try:
        asyncio.run(memory.remember(db, owner_id, "Matheus trabalha na Acme", auto_link=True))
        asyncio.run(memory.remember(db, owner_id, "Matheus gosta de café forte", auto_link=True))
    finally:
        db.close()

    assert brain.chat_calls > 0, "GRAPH_RELATION_LABELS=true must still be able to label"


def test_relinking_the_same_pair_upserts_not_duplicates(owner_id):
    """The idempotency mechanism link() relies on: the SAME (source, target,
    relation) must upsert, never accumulate. This is exactly what made a
    non-deterministic label dangerous under the old default — a re-labeled
    pair no longer matched the dedupe key, so it filed as a second edge
    instead of updating the first. Exercised directly (not through the
    semantic auto-link pipeline, whose ranking is shared-DB/shared-owner
    state across this file's other tests and not what this invariant is about).
    """
    brain = SpyBrain()
    memory = PersistentMemory(brain)
    db = SessionLocal()
    try:
        a = asyncio.run(memory.remember(db, owner_id, "Nó A para teste de dedupe", auto_link=False))
        b = asyncio.run(memory.remember(db, owner_id, "Nó B para teste de dedupe", auto_link=False))

        memory.link(db, owner_id, a.id, b.id, relation="related", weight=0.9, origin="semantic")
        memory.link(db, owner_id, a.id, b.id, relation="related", weight=0.95, origin="semantic")

        neighbours = memory.neighbours(db, owner_id, a.id)
    finally:
        db.close()

    between = [e for e in neighbours["links"] if e["target"] and e["target"]["id"] == b.id]
    assert len(between) == 1, "same (source, target, relation) must upsert, not duplicate"
    assert between[0]["weight"] == 0.95, "upsert should keep the stronger weight"
