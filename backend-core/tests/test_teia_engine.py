"""
The Teia engine — orchestrator, workers and expressions.

Pure engine tests: no database, no kernel services, no network. Custom node types
are registered per test so each behaviour is exercised in isolation.
"""
import asyncio

import pytest
from pydantic import BaseModel

from app.automation.teia.domain.execution import NodeOutput
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.domain.node import Node, NodeMetadata
from app.automation.teia.engine import (
    ExecutionStatus,
    ExpressionError,
    NodeStatus,
    Orchestrator,
    Resolver,
    RunContext,
    RunLimits,
    Services,
)
from app.automation.teia.service import build_registry

# ---------------------------------------------------------------- helpers


def context(payload=None, **limits) -> RunContext:
    return RunContext(
        workflow_id="wf", workflow_slug="teste", execution_id="exec-1", owner_id="dono",
        services=Services(), session_factory=lambda: None,
        trigger_payload=payload or {}, limits=RunLimits(**limits),
    )


def run(workflow: Workflow, registry=None, ctx=None):
    return asyncio.run(
        Orchestrator(registry or build_registry()).run(workflow, ctx or context())
    )


def statuses(result) -> dict[str, str]:
    return {r.node_id: r.status.value for r in result.node_results}


# ---------------------------------------------------------------- expressions


def test_single_expression_keeps_native_type():
    resolver = Resolver({"vars": {"n": 7, "flag": True, "lista": [1, 2]}})
    assert resolver.resolve("{{ vars.n }}") == 7
    assert resolver.resolve("{{ vars.flag }}") is True
    assert resolver.resolve("{{ vars.lista }}") == [1, 2]


def test_interpolation_produces_text():
    resolver = Resolver({"vars": {"nome": "Matheus", "n": 3}})
    assert resolver.resolve("Olá {{ vars.nome }}, {{ vars.n }} itens") == "Olá Matheus, 3 itens"


def test_nested_paths_and_list_indices():
    resolver = Resolver({"trigger": {"a": {"b": [{"c": "achei"}]}}})
    assert resolver.resolve("{{ trigger.a.b.0.c }}") == "achei"


def test_resolves_inside_dicts_and_lists():
    resolver = Resolver({"vars": {"x": 5}})
    assert resolver.resolve({"n": "{{ vars.x }}", "l": ["{{ vars.x }}"]}) == {"n": 5, "l": [5]}


def test_missing_path_is_an_error_not_an_empty_string():
    resolver = Resolver({"vars": {}})
    with pytest.raises(ExpressionError, match="não existe"):
        resolver.resolve("{{ vars.inexistente }}")


def test_default_covers_a_missing_path():
    resolver = Resolver({"vars": {}})
    assert resolver.resolve('{{ vars.nome || "Chefe" }}') == "Chefe"
    assert resolver.resolve("{{ vars.lista || [] }}") == []
    assert resolver.resolve("{{ vars.n || 0 }}") == 0


def test_unknown_root_names_the_available_ones():
    with pytest.raises(ExpressionError, match="raiz desconhecida"):
        Resolver({"vars": {}}).resolve("{{ inventado.x }}")


def test_expressions_cannot_reach_python():
    """A path lookup is not code: attribute access into objects is impossible."""
    resolver = Resolver({"vars": {"obj": object()}})
    with pytest.raises(ExpressionError):
        resolver.resolve("{{ vars.obj.__class__ }}")


def test_secrets_are_tracked_for_redaction():
    resolver = Resolver({"vars": {}}, secret_getter=lambda name: "s3nh4")
    assert resolver.resolve("{{ secret.TOKEN }}") == "s3nh4"
    assert resolver.used_secrets == {"s3nh4"}


def test_missing_secret_says_where_to_put_it():
    resolver = Resolver({"vars": {}}, secret_getter=lambda name: None)
    with pytest.raises(ExpressionError, match="cofre"):
        resolver.resolve("{{ secret.AUSENTE }}")


# ---------------------------------------------------------------- graph running


def test_linear_workflow_runs_in_order():
    wf = Workflow(name="linear")
    a = wf.add_node("inicio", {"dados": {"n": 1}}, id="a")
    b = wf.add_node("texto", {"texto": "n={{ nodes.a.n }}"}, id="b")
    wf.connect(a, b)

    result = run(wf)
    assert result.status is ExecutionStatus.COMPLETED
    assert result.output["b"] == [{"texto": "n=1"}]


def test_trigger_payload_reaches_the_first_node():
    wf = Workflow(name="gatilho")
    wf.add_node("inicio", {}, id="a")
    result = run(wf, ctx=context({"texto": "oi"}))
    assert result.output["a"] == [{"texto": "oi"}]


def test_independent_branches_run_in_parallel():
    """Two 200 ms sleeps on separate branches finish in well under 400 ms."""
    wf = Workflow(name="paralelo")
    start = wf.add_node("inicio", {}, id="a")
    left = wf.add_node("esperar", {"segundos": 0.2}, id="esq")
    right = wf.add_node("esperar", {"segundos": 0.2}, id="dir")
    wf.connect(start, left).connect(start, right)

    result = run(wf, ctx=context(max_parallel=4))
    assert result.status is ExecutionStatus.COMPLETED
    assert result.duration_ms < 380


def test_one_worker_serialises_the_same_graph():
    wf = Workflow(name="serial")
    start = wf.add_node("inicio", {}, id="a")
    wf.connect(start, wf.add_node("esperar", {"segundos": 0.15}, id="esq"))
    wf.connect(start, wf.add_node("esperar", {"segundos": 0.15}, id="dir"))

    result = run(wf, ctx=context(max_parallel=1))
    assert result.duration_ms >= 300


# ---------------------------------------------------------------- branching


def test_if_prunes_the_branch_not_taken():
    wf = Workflow(name="se")
    start = wf.add_node("inicio", {"dados": {"n": 10}}, id="a")
    branch = wf.add_node(
        "se", {"esquerda": "{{ nodes.a.n }}", "operador": "maior", "direita": 5}, id="se"
    )
    yes = wf.add_node("texto", {"texto": "grande"}, id="sim")
    no = wf.add_node("texto", {"texto": "pequeno"}, id="nao")
    wf.connect(start, branch)
    wf.connect(branch, yes, source_port="true")
    wf.connect(branch, no, source_port="false")

    result = run(wf)
    assert statuses(result)["sim"] == "completed"
    assert statuses(result)["nao"] == "skipped"


def test_skip_cascades_down_a_dead_branch():
    wf = Workflow(name="cascata")
    start = wf.add_node("inicio", {"dados": {"n": 1}}, id="a")
    branch = wf.add_node(
        "se", {"esquerda": "{{ nodes.a.n }}", "operador": "maior", "direita": 5}, id="se"
    )
    first = wf.add_node("texto", {"texto": "um"}, id="n1")
    second = wf.add_node("texto", {"texto": "dois"}, id="n2")
    third = wf.add_node("texto", {"texto": "tres"}, id="n3")
    wf.connect(start, branch)
    wf.connect(branch, first, source_port="true")
    wf.connect(first, second).connect(second, third)

    result = run(wf)
    assert [statuses(result)[n] for n in ("n1", "n2", "n3")] == ["skipped"] * 3


def test_merge_does_not_wait_for_a_skipped_branch():
    wf = Workflow(name="juntar")
    start = wf.add_node("inicio", {"dados": {"n": 10}}, id="a")
    branch = wf.add_node(
        "se", {"esquerda": "{{ nodes.a.n }}", "operador": "maior", "direita": 5}, id="se"
    )
    yes = wf.add_node("texto", {"texto": "grande"}, id="sim")
    no = wf.add_node("texto", {"texto": "pequeno"}, id="nao")
    merge = wf.add_node("juntar", {}, id="fim")
    wf.connect(start, branch)
    wf.connect(branch, yes, source_port="true")
    wf.connect(branch, no, source_port="false")
    wf.connect(yes, merge).connect(no, merge)

    result = run(wf)
    assert result.status is ExecutionStatus.COMPLETED
    assert result.output["fim"] == [{"texto": "grande"}]


def test_switch_routes_to_the_first_matching_case():
    wf = Workflow(name="escolher")
    start = wf.add_node("inicio", {"dados": {"tipo": "urgente"}}, id="a")
    switch = wf.add_node("escolher", {
        "valor": "{{ nodes.a.tipo }}",
        "casos": [
            {"porta": "a", "operador": "igual", "valor": "normal"},
            {"porta": "b", "operador": "igual", "valor": "urgente"},
        ],
    }, id="sw")
    wf.connect(start, switch)
    wf.connect(switch, wf.add_node("texto", {"texto": "normal"}, id="n"), source_port="a")
    wf.connect(switch, wf.add_node("texto", {"texto": "urgente"}, id="u"), source_port="b")
    wf.connect(switch, wf.add_node("texto", {"texto": "outro"}, id="d"), source_port="default")

    result = run(wf)
    assert statuses(result)["u"] == "completed"
    assert statuses(result)["n"] == "skipped"
    assert statuses(result)["d"] == "skipped"


# ---------------------------------------------------------------- failure


class _Flaky(Node):
    """Fails a fixed number of times, then succeeds — for the retry tests."""

    metadata = NodeMetadata(type="flaky", name="Flaky", outputs=["main", "error"])

    class Config(BaseModel):
        falhas: int = 1

    config_model = Config
    attempts: dict[str, int] = {}

    async def execute(self, context, inputs):
        seen = _Flaky.attempts.get(context.execution_id, 0) + 1
        _Flaky.attempts[context.execution_id] = seen
        if seen <= self.config.falhas:
            raise RuntimeError(f"falha proposital {seen}")
        return NodeOutput.single({"tentativas": seen})


class _Boom(Node):
    metadata = NodeMetadata(type="boom", name="Boom", outputs=["main", "error"])

    async def execute(self, context, inputs):
        raise RuntimeError("explodiu")


class _Slow(Node):
    metadata = NodeMetadata(type="lento", name="Lento")

    async def execute(self, context, inputs):
        await asyncio.sleep(5)
        return NodeOutput.single({"ok": True})


@pytest.fixture
def registry():
    reg = build_registry()
    reg.register_node(_Flaky)
    reg.register_node(_Boom)
    reg.register_node(_Slow)
    _Flaky.attempts.clear()
    return reg


def test_a_failing_node_fails_the_run_by_default(registry):
    wf = Workflow(name="falha")
    wf.add_node("boom", {}, id="x")
    result = run(wf, registry)
    assert result.status is ExecutionStatus.FAILED
    assert "explodiu" in result.error
    assert "x" in result.summary()


def test_retry_recovers_a_flaky_node(registry):
    wf = Workflow(name="retry")
    wf.add_node(
        "flaky", {"falhas": 2}, id="x",
        policy={"max_attempts": 3, "backoff_seconds": 0},
    )
    result = run(wf, registry)
    assert result.status is ExecutionStatus.COMPLETED
    assert result.node_results[0].attempts == 3


def test_retries_are_bounded(registry):
    wf = Workflow(name="retry-limite")
    wf.add_node(
        "flaky", {"falhas": 9}, id="x",
        policy={"max_attempts": 2, "backoff_seconds": 0},
    )
    result = run(wf, registry)
    assert result.status is ExecutionStatus.FAILED
    assert result.node_results[0].attempts == 2


def test_error_port_turns_a_failure_into_data(registry):
    wf = Workflow(name="porta-erro")
    boom = wf.add_node("boom", {}, id="x")
    handler = wf.add_node("texto", {"texto": "tratei: {{ nodes.x.error }}"}, id="trata")
    wf.connect(boom, handler, source_port="error")

    result = run(wf, registry)
    assert result.status is ExecutionStatus.COMPLETED
    assert "explodiu" in result.output["trata"][0]["texto"]


def test_on_error_continue_keeps_the_rest_running(registry):
    wf = Workflow(name="continuar")
    start = wf.add_node("inicio", {}, id="a")
    boom = wf.add_node("boom", {}, id="x", policy={"on_error": "continue"})
    downstream = wf.add_node("texto", {"texto": "morreu"}, id="depois")
    survivor = wf.add_node("texto", {"texto": "vivo"}, id="vivo")
    wf.connect(start, boom).connect(boom, downstream).connect(start, survivor)

    result = run(wf, registry)
    assert result.status is ExecutionStatus.COMPLETED
    assert statuses(result)["depois"] == "skipped"
    assert statuses(result)["vivo"] == "completed"


def test_node_timeout_is_enforced(registry):
    wf = Workflow(name="timeout")
    wf.add_node("lento", {}, id="x", policy={"timeout_seconds": 0.2})
    result = run(wf, registry)
    assert result.status is ExecutionStatus.FAILED
    assert "tempo esgotado" in result.node_results[0].error


def test_static_bad_config_is_caught_before_running():
    """A literal out-of-range value never even reaches a worker."""
    from app.automation.teia.domain.errors import WorkflowValidationError

    wf = Workflow(name="config-ruim")
    wf.add_node("esperar", {"segundos": 9999}, id="x")
    with pytest.raises(WorkflowValidationError, match="config inválida"):
        run(wf)


def test_config_from_an_expression_is_validated_at_run_time(registry):
    """A `{{ }}` value can only be type-checked once resolved — and it is."""
    wf = Workflow(name="config-runtime")
    start = wf.add_node("inicio", {"dados": {"segundos": 9999}}, id="a")
    slow = wf.add_node(
        "esperar", {"segundos": "{{ nodes.a.segundos }}"}, id="x",
        policy={"max_attempts": 3, "backoff_seconds": 0},
    )
    wf.connect(start, slow)

    result = run(wf, registry)
    assert result.status is ExecutionStatus.FAILED
    failed = next(r for r in result.node_results if r.node_id == "x")
    assert failed.attempts == 1                       # bad config is never retried
    assert "configuração inválida" in failed.error


# ---------------------------------------------------------------- guardrails


def test_run_timeout_stops_a_long_execution(registry):
    wf = Workflow(name="longa")
    wf.add_node("lento", {}, id="x", policy={"timeout_seconds": 30})
    result = run(wf, registry, ctx=context(run_timeout_seconds=0.3))
    assert result.status is ExecutionStatus.FAILED
    assert "interrompida" in result.error


def test_node_budget_stops_a_runaway_graph():
    wf = Workflow(name="muitos")
    start = wf.add_node("inicio", {}, id="a")
    for i in range(12):
        wf.connect(start, wf.add_node("nada", {}, id=f"n{i}"))

    result = run(wf, ctx=context(max_nodes=5))
    assert result.status is ExecutionStatus.FAILED
    assert "limite" in result.error


def test_cancellation_stops_the_run(registry):
    wf = Workflow(name="cancelar")
    start = wf.add_node("inicio", {}, id="a")
    wf.connect(start, wf.add_node("lento", {}, id="x", policy={"timeout_seconds": 10}))

    ctx = context()

    async def scenario():
        task = asyncio.ensure_future(Orchestrator(registry).run(wf, ctx))
        await asyncio.sleep(0.15)
        ctx.cancel.cancel("cancelado pelo dono")
        return await task

    result = asyncio.run(scenario())
    assert result.status is ExecutionStatus.CANCELLED
    assert "cancelado pelo dono" in result.error
    # The point of cancelling: it interrupts the node that is already running,
    # instead of waiting out its 5 seconds.
    assert result.duration_ms < 1500


# ---------------------------------------------------------------- validation


def test_an_invalid_graph_never_reaches_a_worker():
    from app.automation.teia.domain.errors import WorkflowValidationError

    wf = Workflow(name="invalida")
    wf.add_node("tipo_que_nao_existe", {}, id="x")
    with pytest.raises(WorkflowValidationError):
        run(wf)


def test_skipped_nodes_are_not_counted_as_executed():
    wf = Workflow(name="contagem")
    start = wf.add_node("inicio", {"dados": {"n": 1}}, id="a")
    branch = wf.add_node(
        "se", {"esquerda": "{{ nodes.a.n }}", "operador": "maior", "direita": 5}, id="se"
    )
    wf.connect(start, branch)
    wf.connect(branch, wf.add_node("nada", {}, id="morto"), source_port="true")

    result = run(wf)
    assert result.nodes_executed == 2
    assert any(r.status is NodeStatus.SKIPPED for r in result.node_results)
