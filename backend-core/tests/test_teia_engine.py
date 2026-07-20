"""
Teia engine (Phase 2) — execution tests.

Prove the in-process engine really runs a workflow: data flows port to port,
if/branch skips its dead branch, the HTTP node works offline via an injected
httpx transport, failures fail-fast, and invalid workflows are rejected before
any node runs.
"""
import httpx
import pytest

from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine import Engine, ExecutionStatus, NodeStatus, RunContext
from app.automation.teia.nodes.builtin import builtin_registry


@pytest.fixture
def registry():
    return builtin_registry()


@pytest.fixture
def engine(registry):
    return Engine(registry)


# ---------- catalog ----------

def test_builtin_registry_has_expected_nodes(registry):
    assert registry.node_types() == ["http_request", "if", "noop", "set", "transform"]


# ---------- linear data flow ----------

@pytest.mark.asyncio
async def test_set_then_transform_flow(engine):
    wf = Workflow(name="flow")
    a = wf.add_node("set", {"values": {"name": "ada", "temp": 1}})
    b = wf.add_node("transform", {"rename": {"name": "user"}, "drop": ["temp"]})
    wf.connect(a, b)

    result = await engine.run(wf)

    assert result.status is ExecutionStatus.SUCCESS
    assert result.output_of(b.id).port("main") == [{"user": "ada"}]


@pytest.mark.asyncio
async def test_trigger_items_seed_entry_node(engine):
    wf = Workflow(name="seeded")
    a = wf.add_node("set", {"values": {"seen": True}})
    result = await engine.run(wf, trigger_items=[{"id": 1}, {"id": 2}])
    assert result.output_of(a.id).port("main") == [
        {"id": 1, "seen": True},
        {"id": 2, "seen": True},
    ]


# ---------- branching ----------

@pytest.mark.asyncio
async def test_if_branch_skips_dead_path(engine):
    wf = Workflow(name="branch")
    src = wf.add_node("set", {"values": {"value": 10}})
    gate = wf.add_node("if", {"field": "value", "operator": "gt", "value": 5})
    on_true = wf.add_node("set", {"values": {"hit": "yes"}})
    on_false = wf.add_node("set", {"values": {"hit": "no"}})
    wf.connect(src, gate)
    wf.connect(gate, on_true, source_port="true")
    wf.connect(gate, on_false, source_port="false")

    result = await engine.run(wf)

    assert result.results[on_true.id].status is NodeStatus.SUCCESS
    assert result.results[on_false.id].status is NodeStatus.SKIPPED
    assert result.output_of(on_true.id).port("main")[0]["hit"] == "yes"


# ---------- HTTP node (offline, deterministic) ----------

@pytest.mark.asyncio
async def test_http_node_with_injected_transport(engine):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ping"
        return httpx.Response(200, json={"pong": True})

    wf = Workflow(name="http")
    node = wf.add_node("http_request", {"method": "GET", "url": "https://example.test/ping"})
    ctx = RunContext(wf.id, "exec_test", http_transport=httpx.MockTransport(handler))

    result = await engine.run(wf, context=ctx)

    item = result.output_of(node.id).port("main")[0]
    assert item["status_code"] == 200
    assert item["body"] == {"pong": True}


# ---------- failure handling ----------

@pytest.mark.asyncio
async def test_failure_is_fail_fast(engine):
    # http_request with no transport hitting an unroutable host -> the node raises;
    # a downstream node must be marked skipped and the run marked error.
    wf = Workflow(name="boom")
    bad = wf.add_node("http_request", {"url": "http://127.0.0.1:1/never"})
    after = wf.add_node("noop")
    wf.connect(bad, after)

    result = await engine.run(wf)

    assert result.status is ExecutionStatus.ERROR
    assert result.results[bad.id].status is NodeStatus.ERROR
    assert result.results[bad.id].error
    assert result.results[after.id].status is NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_invalid_workflow_is_rejected_before_running(engine):
    wf = Workflow(name="invalid")
    wf.add_node("set", {})
    wf.connect("ghost_a", "ghost_b")  # dangling connection
    with pytest.raises(WorkflowValidationError):
        await engine.run(wf)
