"""
Teia domain core (Phase 1) — contract tests.

Pure domain: no Ollama, no DB, no engine. They prove a workflow can be built in
code, serialized to/from JSON and YAML losslessly, ordered topologically, checked
for cycles, and validated both structurally and against a registry.
"""
import pytest
from pydantic import BaseModel, ValidationError

from app.automation.teia.domain import (
    Node,
    NodeMetadata,
    NodeOutput,
    Trigger,
    TriggerMetadata,
    Workflow,
    WorkflowCycleError,
)
from app.automation.teia.registry import Registry
from app.automation.teia.serialization import (
    from_json,
    from_yaml,
    to_dict,
    to_json,
    to_yaml,
)

# ---------- sample node/trigger types (what plugins will provide later) ----------

class _EchoConfig(BaseModel):
    message: str
    times: int = 1


class EchoNode(Node):
    metadata = NodeMetadata(
        type="echo", name="Echo", category="test", inputs=["main"], outputs=["main", "error"]
    )
    config_model = _EchoConfig

    async def execute(self, context, inputs):  # not exercised in Phase 1
        return NodeOutput.single(self.validate_config({}).message)


class NoOpNode(Node):
    metadata = NodeMetadata(type="noop", name="No-op")

    async def execute(self, context, inputs):
        return NodeOutput()


class TickTrigger(Trigger):
    metadata = TriggerMetadata(type="tick", name="Tick")


@pytest.fixture
def registry() -> Registry:
    reg = Registry()
    reg.register_node(EchoNode)
    reg.register_node(NoOpNode)
    reg.register_trigger(TickTrigger)
    return reg


# ---------- metadata / config ----------

def test_node_metadata_rejects_duplicate_ports():
    with pytest.raises(ValidationError):
        NodeMetadata(type="x", name="X", outputs=["main", "main"])


def test_node_config_validation():
    node = EchoNode()
    assert node.validate_config({"message": "oi", "times": 3}).times == 3
    with pytest.raises(ValidationError):
        node.validate_config({})  # missing required 'message'


# ---------- registry ----------

def test_registry_register_and_lookup(registry):
    assert registry.get_node("echo") is EchoNode
    assert registry.get_trigger("tick") is TickTrigger
    assert registry.get_node("ghost") is None
    assert registry.node_types() == ["echo", "noop"]
    assert registry.trigger_types() == ["tick"]


def test_registry_rejects_node_without_metadata():
    class Bad(Node):
        async def execute(self, context, inputs):
            return NodeOutput()

    Bad.metadata = None  # type: ignore[assignment]
    with pytest.raises(ValueError):
        Registry().register_node(Bad)


# ---------- builders + graph algorithms ----------

def test_build_and_topological_order():
    wf = Workflow(name="diamante")
    a = wf.add_node("noop", name="A")
    b = wf.add_node("noop", name="B")
    c = wf.add_node("noop", name="C")
    d = wf.add_node("noop", name="D")
    wf.connect(a, b).connect(a, c).connect(b, d).connect(c, d)

    order = wf.topological_order()
    assert order[0] == a.id and order[-1] == d.id
    assert order.index(b.id) < order.index(d.id)
    assert wf.entry_nodes() == [a.id]
    assert set(wf.successors(a.id)) == {b.id, c.id}
    assert wf.predecessors(d.id) == [b.id, c.id]
    assert wf.has_cycle() is False


def test_cycle_detection():
    wf = Workflow(name="ciclo")
    a = wf.add_node("noop")
    b = wf.add_node("noop")
    wf.connect(a, b).connect(b, a)
    assert wf.has_cycle() is True
    with pytest.raises(WorkflowCycleError):
        wf.topological_order()


# ---------- serialization round-trips ----------

def test_json_roundtrip_is_lossless():
    wf = Workflow(name="rt")
    a = wf.add_node("echo", {"message": "olá"}, name="A")
    b = wf.add_node("noop", name="B")
    wf.connect(a, b)
    wf.add_trigger("tick", a)

    restored = from_json(to_json(wf))
    assert to_dict(restored) == to_dict(wf)
    assert restored.node(a.id).config == {"message": "olá"}


def test_yaml_roundtrip_is_lossless():
    wf = Workflow(name="rt-yaml")
    a = wf.add_node("noop")
    b = wf.add_node("noop")
    wf.connect(a, b)
    restored = from_yaml(to_yaml(wf))
    assert to_dict(restored) == to_dict(wf)


# ---------- validation ----------

def test_valid_workflow_passes_with_catalog(registry):
    wf = Workflow(name="ok")
    a = wf.add_node("echo", {"message": "oi"})
    b = wf.add_node("noop")
    wf.connect(a, b, source_port="main", target_port="main")
    wf.add_trigger("tick", a)
    assert wf.validate_graph(registry) == []
    assert wf.is_valid(registry) is True


def test_structural_problems_without_catalog():
    wf = Workflow(name="ruim")
    a = wf.add_node("noop", id="dup")
    wf.add_node("noop", id="dup")               # duplicate id
    wf.connect(a, "fantasma")                    # dangling target
    wf.add_trigger("tick", "inexistente")        # trigger to missing node
    problems = wf.validate_graph()
    assert any("duplicado" in p for p in problems)
    assert any("destino inexistente" in p for p in problems)
    assert any("aponta para nó inexistente" in p for p in problems)


def test_catalog_problems(registry):
    wf = Workflow(name="ruim2")
    ghost = wf.add_node("ghost")                 # unknown node type
    bad = wf.add_node("echo", {"times": 2})       # invalid config (no 'message')
    wf.connect(bad, ghost, source_port="inexistente")  # unknown output port
    wf.add_trigger("desconhecido", bad)           # unknown trigger type
    problems = wf.validate_graph(registry)
    assert any("tipo de nó desconhecido" in p for p in problems)
    assert any("config inválida" in p for p in problems)
    assert any("porta de saída inexistente" in p for p in problems)
    assert any("tipo de gatilho desconhecido" in p for p in problems)
