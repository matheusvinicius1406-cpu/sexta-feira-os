"""
The kernel audit, enforced.

`scripts/audit_kernel.py` hunts for defects that do not raise: wiring guarded on
something that does not exist yet, features stranded on a dead branch, ORM fields
that are not columns, assertions a test can skip, and tests that read the machine
instead of controlling it. Every check generalises a bug this repository actually
shipped.

These tests do two things:

  * assert the audit is clean on the current tree, so the classes stay closed;
  * assert each check still FIRES on a synthetic example of its own bug — because
    a checker that silently stops matching is the very failure mode being hunted,
    and "zero findings" would otherwise be indistinguishable from "broken".
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
AUDIT = BACKEND / "scripts" / "audit_kernel.py"


def load_audit(root: Path):
    """Import the audit fresh, pointed at `root`.

    The module is registered in `sys.modules` before it executes: its `@dataclass`
    resolves annotations through `sys.modules[cls.__module__]`, which is None for
    a module that was never registered.
    """
    name = f"audit_kernel_{abs(hash(str(root)))}"
    argv, sys.argv = sys.argv, ["audit_kernel.py", str(root)]
    try:
        spec = importlib.util.spec_from_file_location(name, AUDIT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
        return module
    finally:
        sys.argv = argv


def run_all(root: Path) -> list:
    audit = load_audit(root)
    audit.check_pipeline_wiring()
    audit.check_dead_fallback()
    audit.check_phantom_orm_fields()
    audit.check_conditional_assertions()
    audit.check_ambient_tests()
    return audit.findings


# ---------------------------------------------------------------- the real tree


def test_kernel_is_clean():
    problems = run_all(BACKEND)
    assert problems == [], "\n" + "\n".join(
        f"  [{p.check}] {p.file}:{p.line}\n      {p.message}" for p in problems
    )


# ---------------------------------------------------------------- the checks work


@pytest.fixture
def fake_tree(tmp_path: Path) -> Path:
    """A miniature project reproducing every bug class, for the checks to find."""
    app = tmp_path / "app"
    (app / "kernel" / "pipeline" / "steps").mkdir(parents=True)
    (app / "models").mkdir(parents=True)
    (app / "brain").mkdir(parents=True)
    tests = tmp_path / "tests"
    tests.mkdir()

    (app / "kernel" / "pipeline" / "startup.py").write_text(
        "class StartupPipeline:\n"
        "    DEFAULT_STEPS = [EventBusStep, WorldModelStep, PlanningStep, DecisionStep]\n",
        encoding="utf-8",
    )
    # Two ways to touch a dependency too early: guarding on it, and handing it
    # to a collaborator. The second is quieter — no visible dead branch, just a
    # service holding None — and it is the one that hid the missing briefing
    # focus, so the fixture has to reproduce both.
    (app / "kernel" / "pipeline" / "steps" / "core_steps.py").write_text(
        "class EventBusStep:\n"
        "    async def execute(self, kernel):\n"
        "        kernel.events = 1\n"
        "        if kernel.world:\n"
        "            kernel.events.subscribe()\n"
        "\n"
        "class WorldModelStep:\n"
        "    async def execute(self, kernel):\n"
        "        kernel.world = 2\n"
        "\n"
        "class PlanningStep:\n"
        "    async def execute(self, kernel):\n"
        "        kernel.planning = Planning()\n"
        "        kernel.briefing = Briefing(decision=kernel.decision)\n"
        "\n"
        "class DecisionStep:\n"
        "    async def execute(self, kernel):\n"
        "        kernel.decision = Decision(planning=kernel.planning)\n",
        encoding="utf-8",
    )
    (app / "models" / "models.py").write_text(
        "class Owner:\n"
        "    id = Column(String)\n"
        "    email = Column(String)\n",
        encoding="utf-8",
    )
    # A model built with a keyword that is not a column.
    (app / "brain" / "auth.py").write_text(
        "def make():\n"
        "    return Owner(id='x', email='a@b', display_name='nope')\n",
        encoding="utf-8",
    )
    # An injected collaborator that strands the code below it — inside a try,
    # where a top-level-only scan would miss it.
    (app / "brain" / "cognition.py").write_text(
        "class Cognition:\n"
        "    def __init__(self, brain, extractor=None):\n"
        "        self.brain = brain\n"
        "        self.extractor = extractor\n"
        "    async def learn(self, db, text):\n"
        "        try:\n"
        "            if self.extractor:\n"
        "                await self.extractor.extract(db, text)\n"
        "                return\n"
        "            probe = [{'role': 'system', 'content': 'x'}]\n"
        "            fact = await self.brain.chat(probe, temperature=0.1)\n"
        "            if fact and len(fact) > 8:\n"
        "                await self.memory.remember(db, fact, kind='fact')\n"
        "                export(vault=1, title=fact, content=fact, kind='fact')\n"
        "        except Exception:\n"
        "            pass\n",
        encoding="utf-8",
    )
    # An assertion that only runs if the request happened to succeed.
    (tests / "test_thing.py").write_text(
        "def test_export(client):\n"
        "    try:\n"
        "        r = client.post('/x')\n"
        "        if r.status_code == 200:\n"
        "            assert 'a' in r.text\n"
        "    finally:\n"
        "        pass\n",
        encoding="utf-8",
    )
    # A 503 test that forces nothing.
    (tests / "test_degrade.py").write_text(
        "def test_degrades(client):\n"
        "    r = client.post('/chat')\n"
        "    assert r.status_code == 503\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize(
    "check",
    [
        "wiring-before-exists",
        "dead-fallback",
        "phantom-orm-field",
        "skippable-assertion",
        "ambient-test",
    ],
)
def test_each_check_still_catches_its_bug(fake_tree: Path, check: str):
    found = {f.check for f in run_all(fake_tree)}
    assert check in found, (
        f"a checagem '{check}' parou de encontrar o próprio bug — "
        f"encontradas: {sorted(found) or 'nenhuma'}"
    )


def test_wiring_check_catches_a_dependency_passed_on_too_early(fake_tree: Path):
    """The guard variant firing does not prove the `passes` variant does.

    Both report under `wiring-before-exists`, so the parametrised test above is
    satisfied by the guard case alone — and the pass case could rot unnoticed.
    This one names it: the step that hands `kernel.decision` to a collaborator
    before it exists must be reported, and reported as passing rather than
    guarding, since the two have different fixes.
    """
    passed_on = [
        f for f in run_all(fake_tree)
        if f.check == "wiring-before-exists" and "passes on `kernel.decision`" in f.message
    ]
    assert passed_on, (
        "PlanningStep entrega `kernel.decision` antes de DecisionStep criá-lo e "
        "a auditoria não reclamou — o colaborador recebe None em silêncio."
    )


def test_wiring_check_ignores_a_dependency_the_step_already_built(fake_tree: Path):
    """DecisionStep passes `kernel.planning`, which an EARLIER step assigned.

    That is correct wiring, and the check must stay quiet about it — otherwise
    every legitimate injection in the pipeline becomes a finding and the audit
    gets ignored, which is the same as not having one.
    """
    noise = [f for f in run_all(fake_tree) if "kernel.planning" in f.message]
    assert noise == [], f"falso positivo: {[f.message for f in noise]}"


def test_a_test_that_forces_the_failure_is_not_flagged(fake_tree: Path):
    """The refinement that stopped flagging the voice tests must hold."""
    (fake_tree / "tests" / "test_degrade.py").write_text(
        "def test_degrades(client, monkeypatch):\n"
        "    voice.synthesizer.speak = boom\n"
        "    r = client.post('/speak')\n"
        "    assert r.status_code == 503\n",
        encoding="utf-8",
    )
    ambient = [f for f in run_all(fake_tree) if f.check == "ambient-test"]
    assert ambient == [], f"falso positivo: {[f.file for f in ambient]}"
