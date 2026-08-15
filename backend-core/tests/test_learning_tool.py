"""
record_learning must not lose what the agent tried to register.

The autonomous pulse surfaced this live: the (small) brain called
`record_learning` with `{"content": ...}` — the natural guess — while the
tool schema requires `context`. The handler passed "" as context and
`record()` raised "learning needs a context", so the pulse's autonomous
execution failed with a bug that only shows when the agent acts alone.
"""
import asyncio

from app.brain.tools import ToolKit


class _FakeLearning:
    def __init__(self):
        self.calls = []

    async def record(
        self, db, owner_id, context, *,
        observation=None, quality=0.5, lesson=None,
        kind="outcome", tag=None, ref_id=None, source="kernel",
    ):
        self.calls.append({
            "context": context, "observation": observation,
            "quality": quality, "lesson": lesson, "tag": tag, "source": source,
        })
        # A `class _Entry: quality = quality` aqui seria NameError (corpo de
        # classe não enxerga escopo de função); objeto simples resolve.
        return type("Entry", (), {"quality": quality})()


def test_record_learning_accepts_content_as_context():
    learn = _FakeLearning()
    tk = ToolKit(memory=None, automations=None, learning=learn)
    out = asyncio.run(tk.dispatch(
        "record_learning",
        {"content": "Matheus prefere trabalhar de casa e tem rotina de exercício."},
        None, "owner",
    ))
    assert "registrado" in out
    assert learn.calls[0]["context"] == "Matheus prefere trabalhar de casa e tem rotina de exercício."
    # A lição também não se perde: `lesson` cai no mesmo texto do agente.
    assert learn.calls[0]["lesson"] == learn.calls[0]["context"]


def test_record_learning_with_real_fields_wins():
    learn = _FakeLearning()
    tk = ToolKit(memory=None, automations=None, learning=learn)
    asyncio.run(tk.dispatch(
        "record_learning",
        {"context": "ctx real", "lesson": "lição", "quality": 0.9, "tag": "rotina"},
        None, "owner",
    ))
    c = learn.calls[0]
    assert c["context"] == "ctx real"
    assert c["lesson"] == "lição"
    assert c["quality"] == 0.9
    assert c["tag"] == "rotina"
