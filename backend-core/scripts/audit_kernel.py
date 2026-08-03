"""
Kernel audit — hunt for the bug classes that hide instead of crashing.

Every check here generalises a defect actually found in this codebase. They all
share one trait: the code runs, nothing raises, and a feature is simply absent.

  1. WIRING-BEFORE-EXISTS
     A startup step guards on `kernel.x` that a LATER step assigns, so the guard
     is always False and the wiring silently never happens.
     Found: EventBusStep subscribed the World Model projector under
     `if kernel.world:` while WorldModelStep still hadn't run. Events never
     touched the world.

  2. DEAD FALLBACK
     A method returns early on the path the kernel always takes, leaving a large
     block below that only a never-used configuration reaches.
     Found: Cognition._auto_learn returned right after `extractor.extract(...)`,
     so the Obsidian auto-export below it never ran — in any kernel.

  3. PHANTOM ORM FIELD
     A model is constructed with a keyword the table does not define. Raises only
     when that branch is finally taken.
     Found: the auth dev-bypass built `Owner(display_name=...)`; Owner has no
     such column, and no id default either.

  4. ASSERTION THAT CAN BE SKIPPED
     A test whose assert sits under an `if`, so it reports success by not
     checking anything.
     Found: test_auto_export_integration_via_cognition asserted inside
     `if r.status_code == 200:` — and the status was 503.

  5. AMBIENT-DEPENDENT TEST
     A test that reads a live service (Ollama, a port) instead of controlling it,
     so it passes or fails with the machine rather than with the code.

Usage:
    python scripts/audit_kernel.py          # report
    python scripts/audit_kernel.py --strict # exit 1 if anything is found
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _roots(base: Path) -> tuple[Path, Path, Path]:
    return base, base / "app", base / "tests"


# Overridable so the audit can be pointed at a reconstructed older tree — which
# is the only honest way to know a check works rather than merely returns zero.
ROOT, APP, TESTS = _roots(
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
    else Path(__file__).resolve().parent.parent
)


@dataclass
class Finding:
    check: str
    file: str
    line: int
    message: str


findings: list[Finding] = []


def report(check: str, path: Path, line: int, message: str) -> None:
    findings.append(Finding(check, str(path.relative_to(ROOT)).replace("\\", "/"), line, message))


def parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None


# ─────────────────────────────────────────────────────────────
# 1 — Wiring before the dependency exists
# ─────────────────────────────────────────────────────────────


def _step_order() -> list[str]:
    """The order StartupPipeline actually runs its steps in."""
    startup = ROOT / "app" / "kernel" / "pipeline" / "startup.py"
    tree = parse(startup)
    if tree is None:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "DEFAULT_STEPS":
            return [e.id for e in node.value.elts if isinstance(e, ast.Name)]
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if getattr(t, "id", "") == "DEFAULT_STEPS":
                    return [e.id for e in node.value.elts if isinstance(e, ast.Name)]
    return []


@dataclass
class StepFacts:
    assigns: set[str] = field(default_factory=set)
    guards: dict[str, int] = field(default_factory=dict)   # attr -> line of the guard
    passes: dict[str, int] = field(default_factory=dict)   # attr -> line it is passed on


def _kernel_attr(node: ast.AST) -> str | None:
    """`kernel.foo` → 'foo'."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id == "kernel":
            return node.attr
    return None


def check_pipeline_wiring() -> None:
    steps_file = APP / "kernel" / "pipeline" / "steps" / "core_steps.py"
    tree = parse(steps_file)
    order = _step_order()
    if tree is None or not order:
        return

    facts: dict[str, StepFacts] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        f = StepFacts()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    attr = _kernel_attr(t)
                    if attr:
                        f.assigns.add(attr)
            # `if kernel.x:` and `if kernel.x and ...:`
            if isinstance(sub, ast.If):
                for test_node in ast.walk(sub.test):
                    attr = _kernel_attr(test_node)
                    if attr:
                        f.guards.setdefault(attr, sub.lineno)
            # `Service(dep=kernel.x)` / `Service(kernel.x)` — handing a
            # collaborator on rather than testing it.
            if isinstance(sub, ast.Call):
                for arg in [*sub.args, *(kw.value for kw in sub.keywords)]:
                    attr = _kernel_attr(arg)
                    if attr:
                        f.passes.setdefault(attr, sub.lineno)
        facts[node.name] = f

    position = {name: i for i, name in enumerate(order)}

    # Guarding is one way to touch something too early; handing it to a
    # collaborator is the other, and it is quieter still — the guard at least
    # leaves a visible branch, while `Service(dep=kernel.x)` just injects None
    # and lets the service degrade exactly as it would if the feature were off.
    # Found this way: PlanningStep built the BriefingService with
    # `decision=kernel.decision` one step before DecisionStep assigned it, so
    # the briefing's "Foco sugerido" section never rendered, in any kernel.
    kinds = (
        ("guards on", "guards", "the guard is always False and whatever it protects never runs"),
        ("passes on", "passes", "the collaborator silently receives None"),
    )
    for step_name, f in facts.items():
        if step_name not in position:
            continue
        for verb, attr_name, consequence in kinds:
            for attr, line in getattr(f, attr_name).items():
                if attr in f.assigns:
                    continue  # the step builds it itself
                if attr_name == "passes" and attr in f.guards:
                    continue  # already diagnosed, more precisely, as a guard
                producers = [
                    other for other, of in facts.items()
                    if attr in of.assigns and other in position
                ]
                if not producers:
                    continue
                earliest = min(position[p] for p in producers)
                if position[step_name] < earliest:
                    owner = min(producers, key=lambda p: position[p])
                    report(
                        "wiring-before-exists", steps_file, line,
                        f"{step_name} {verb} `kernel.{attr}`, but {owner} only assigns it "
                        f"later in DEFAULT_STEPS — {consequence}.",
                    )


# ─────────────────────────────────────────────────────────────
# 2 — Dead fallback below an early return
# ─────────────────────────────────────────────────────────────


def _optional_dependencies(cls: ast.ClassDef) -> set[str]:
    """Attributes assigned in __init__ from a parameter that DEFAULTS TO None.

    That is the signature of an injected collaborator, as opposed to a plain
    state flag like `self.aborted`. Only the former produces the dead-fallback
    bug: the kernel always supplies it, so the `is None` branch never runs.
    """
    optional: set[str] = set()
    for fn in cls.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name != "__init__":
            continue
        args = fn.args
        defaults = dict(
            zip([a.arg for a in args.args[-len(args.defaults):]] if args.defaults else [],
                args.defaults, strict=False)
        )
        for kwarg, default in zip(
            [a.arg for a in args.kwonlyargs], args.kw_defaults, strict=False
        ):
            if default is not None:
                defaults[kwarg] = default
        none_params = {
            name for name, node in defaults.items()
            if isinstance(node, ast.Constant) and node.value is None
        }
        for stmt in ast.walk(fn):
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Name):
                if stmt.value.id in none_params:
                    for t in stmt.targets:
                        if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                                and t.value.id == "self"):
                            optional.add(t.attr)
    return optional


def _statement_blocks(node: ast.AST) -> list[list[ast.stmt]]:
    """Every ordered statement list under `node` — bodies, else-branches, handlers.

    Checks that only inspect `fn.body` miss anything nested in a `try:` or `with:`.
    Both historical occurrences of the dead-fallback and skippable-assertion bugs
    were nested exactly that way, so a top-level-only scan reported zero findings
    while appearing to work — the same silent no-op this audit exists to catch.
    """
    blocks: list[list[ast.stmt]] = []
    for sub in ast.walk(node):
        for attr in ("body", "orelse", "finalbody"):
            value = getattr(sub, attr, None)
            if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                blocks.append(value)
    return blocks


def check_dead_fallback() -> None:
    """`if self.<injected>: ...; return` followed by a substantial block below.

    Restricted to attributes that come from an optional constructor parameter.
    Guarding on a state flag (`self.aborted`, `self._ready`) and returning is
    ordinary control flow, not a dead branch — flagging those was noise.
    """
    for path in sorted(APP.rglob("*.py")):
        tree = parse(path)
        if tree is None:
            continue
        for cls in ast.walk(tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            injected = _optional_dependencies(cls)
            if not injected:
                continue
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for block in _statement_blocks(fn):
                    for i, stmt in enumerate(block):
                        if not isinstance(stmt, ast.If) or stmt.orelse:
                            continue
                        guard = stmt.test
                        if not (isinstance(guard, ast.Attribute)
                                and isinstance(guard.value, ast.Name)
                                and guard.value.id == "self"
                                and guard.attr in injected):
                            continue
                        if not any(isinstance(s, ast.Return) for s in stmt.body):
                            continue
                        tail = block[i + 1:]
                        weight = sum(len(list(ast.walk(s))) for s in tail)
                        if len(tail) >= 2 and weight >= 25:
                            report(
                                "dead-fallback", path, stmt.lineno,
                                f"{cls.name}.{fn.name}() returns as soon as "
                                f"`self.{guard.attr}` is set, leaving {len(tail)} statement(s) "
                                f"below reachable only when it is None. The kernel always "
                                f"injects it, so that code never runs.",
                            )


# ─────────────────────────────────────────────────────────────
# 3 — Phantom ORM field
# ─────────────────────────────────────────────────────────────


def _orm_columns() -> dict[str, set[str]]:
    models = APP / "models" / "models.py"
    tree = parse(models)
    out: dict[str, set[str]] = {}
    if tree is None:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        cols: set[str] = set()
        for sub in node.body:
            if isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Call):
                fn = sub.value.func
                name = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if name in ("Column", "relationship"):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            cols.add(t.id)
        if cols:
            out[node.name] = cols
    return out


def check_phantom_orm_fields() -> None:
    columns = _orm_columns()
    if not columns:
        return
    for path in sorted([*APP.rglob("*.py"), *TESTS.rglob("*.py")]):
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            model = node.func.id
            if model not in columns:
                continue
            for kw in node.keywords:
                if kw.arg and kw.arg not in columns[model]:
                    report(
                        "phantom-orm-field", path, node.lineno,
                        f"{model}(...) is given `{kw.arg}=`, which {model} does not define. "
                        f"This raises the first time this branch is taken.",
                    )


# ─────────────────────────────────────────────────────────────
# 4 — Assertions that can be skipped
# ─────────────────────────────────────────────────────────────


def check_conditional_assertions() -> None:
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = parse(path)
        if tree is None:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not fn.name.startswith("test_"):
                continue
            # An assert reachable only through an `if` is an assert the test can
            # skip. Scanned across nested blocks, not just fn.body: the real case
            # sat inside a try/finally, where a top-level-only scan saw nothing.
            guarded: set[int] = set()
            for stmt in ast.walk(fn):
                if isinstance(stmt, ast.If):
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Assert):
                            guarded.add(sub.lineno)
            all_asserts = {
                s.lineno for s in ast.walk(fn) if isinstance(s, ast.Assert)
            }
            unconditional = all_asserts - guarded
            conditional = sorted(guarded)
            if conditional and not unconditional:
                report(
                    "skippable-assertion", path, conditional[0],
                    f"{fn.name}() only asserts inside an `if` — when the condition is False "
                    f"the test passes having verified nothing.",
                )


# ─────────────────────────────────────────────────────────────
# 5 — Tests that read ambient state
# ─────────────────────────────────────────────────────────────

def check_ambient_tests() -> None:
    """A test asserting the 503 "brain is down" path must FORCE the brain down.

    Matching prose in comments was useless — it flagged docstrings that merely
    said a test needs no Ollama. What actually identifies the bug is structural:
    the test asserts 503 and never puts the brain offline, so it only passes on a
    machine where Ollama happens not to be running.
    """
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = parse(path)
        if tree is None:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not fn.name.startswith("test_"):
                continue
            asserts_503 = any(
                isinstance(n, ast.Constant) and n.value == 503 for n in ast.walk(fn)
            )
            if not asserts_503:
                continue

            # A 503 test is sound as long as it FORCES the failure, by any means:
            # the brain_offline helper, raising a *Unavailable, or stubbing a
            # collaborator. Only requiring brain_offline flagged the voice tests,
            # which force the voice engine down instead — equally deterministic.
            body = ast.dump(fn)
            forces_failure = (
                "brain_offline" in body
                or "Unavailable" in body
                or any(
                    isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Attribute) for t in n.targets)
                    for n in ast.walk(fn)
                )
            )
            if not forces_failure:
                report(
                    "ambient-test", path, fn.lineno,
                    f"{fn.name}() asserts the 503 degradation path without forcing the brain "
                    f"down — it passes only where Ollama happens to be absent. Wrap the call "
                    f"in tests.conftest.brain_offline().",
                )


# ─────────────────────────────────────────────────────────────


def main() -> int:
    check_pipeline_wiring()
    check_dead_fallback()
    check_phantom_orm_fields()
    check_conditional_assertions()
    check_ambient_tests()

    if not findings:
        print("audit: nada encontrado")
        return 0

    by_check: dict[str, list[Finding]] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)

    for check in sorted(by_check):
        items = by_check[check]
        print(f"\n{check}  ({len(items)})")
        print("-" * (len(check) + 8))
        for f in items:
            print(f"  {f.file}:{f.line}")
            print(f"      {f.message}")

    print(f"\ntotal: {len(findings)}")
    return 1 if "--strict" in sys.argv else 0


if __name__ == "__main__":
    raise SystemExit(main())
