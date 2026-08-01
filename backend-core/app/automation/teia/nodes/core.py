"""
Core flow nodes — start, branch, merge, wait, stop.

These are the nodes that give a workflow its shape. None of them touch the
outside world; they decide where the data goes.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata

# ---------------------------------------------------------------- comparisons


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "não", "nao", "no", "none", "null")
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return bool(value)


Operator = Literal[
    "igual", "diferente", "maior", "maior_igual", "menor", "menor_igual",
    "contem", "nao_contem", "comeca_com", "termina_com", "regex",
    "vazio", "nao_vazio", "verdadeiro", "falso", "esta_em",
]


def compare(left: Any, operator: str, right: Any) -> bool:
    """Evaluate one condition. Numeric comparisons coerce; the rest use text."""
    if operator == "vazio":
        return not _truthy(left)
    if operator == "nao_vazio":
        return _truthy(left)
    if operator == "verdadeiro":
        return _truthy(left)
    if operator == "falso":
        return not _truthy(left)

    if operator in ("maior", "maior_igual", "menor", "menor_igual"):
        a, b = _as_number(left), _as_number(right)
        if a is None or b is None:
            raise ValueError(
                f"'{operator}' precisa de números; recebi {left!r} e {right!r}"
            )
        return {
            "maior": a > b, "maior_igual": a >= b,
            "menor": a < b, "menor_igual": a <= b,
        }[operator]

    if operator == "igual":
        a, b = _as_number(left), _as_number(right)
        if a is not None and b is not None:
            return a == b
        return str(left) == str(right)
    if operator == "diferente":
        return not compare(left, "igual", right)

    if operator == "esta_em":
        haystack = right if isinstance(right, (list, tuple, set)) else str(right).split(",")
        return any(str(left).strip() == str(x).strip() for x in haystack)

    text, needle = str(left), str(right)
    if operator == "contem":
        return needle.lower() in text.lower()
    if operator == "nao_contem":
        return needle.lower() not in text.lower()
    if operator == "comeca_com":
        return text.lower().startswith(needle.lower())
    if operator == "termina_com":
        return text.lower().endswith(needle.lower())
    if operator == "regex":
        return re.search(needle, text) is not None

    raise ValueError(f"operador desconhecido: '{operator}'")


# ---------------------------------------------------------------- nodes


class _StartConfig(BaseModel):
    """Optional constants merged into the item this node emits."""

    dados: dict = Field(default_factory=dict)


class StartNode(Node):
    """The entry point: emits whatever started the run, plus any fixed `dados`."""

    metadata = NodeMetadata(
        type="inicio", name="Início", category="fluxo",
        description="Ponto de entrada. Emite os dados do gatilho como um item.",
        inputs=[], outputs=["main"],
    )
    config_model = _StartConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        item = {**context.trigger_payload, **self.config.dados}
        return NodeOutput.single(item)


class _SetVarsConfig(BaseModel):
    variaveis: dict = Field(default_factory=dict)


class SetVarsNode(Node):
    """Write workflow variables, readable downstream as `{{ vars.nome }}`."""

    metadata = NodeMetadata(
        type="definir_variaveis", name="Definir variáveis", category="fluxo",
        description="Grava valores em vars.* para os nós seguintes usarem.",
    )
    config_model = _SetVarsConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        context.variables.update(self.config.variaveis)
        passthrough = inputs.port("main") or [self.config.variaveis]
        return NodeOutput(items={"main": passthrough})


class _IfConfig(BaseModel):
    esquerda: Any = None
    operador: Operator = "verdadeiro"
    direita: Any = None


class IfNode(Node):
    """Two-way branch: items leave by `true` or by `false`, never both.

    The port that doesn't fire emits nothing, so the orchestrator skips that whole
    branch instead of running it with empty input.
    """

    metadata = NodeMetadata(
        type="se", name="Se", category="fluxo",
        description="Desvia o fluxo conforme uma condição.",
        inputs=["main"], outputs=["true", "false"],
    )
    config_model = _IfConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        cfg = self.config
        passed = compare(cfg.esquerda, cfg.operador, cfg.direita)
        items = inputs.port("main") or [{}]
        context.log(f"condição {cfg.operador} → {'verdadeiro' if passed else 'falso'}")
        return NodeOutput(items={"true" if passed else "false": items})


class _SwitchCase(BaseModel):
    porta: str = Field(..., min_length=1)
    operador: Operator = "igual"
    valor: Any = None


class _SwitchConfig(BaseModel):
    valor: Any = None
    casos: list[_SwitchCase] = Field(default_factory=list)


class SwitchNode(Node):
    """Many-way branch: the first matching case wins, else `default`.

    Cases route to named ports; declare the same names in the connections. Any
    port that isn't the winner stays silent, so its branch is skipped.
    """

    metadata = NodeMetadata(
        type="escolher", name="Escolher", category="fluxo",
        description="Roteia para a primeira porta cujo caso casar (senão 'default').",
        inputs=["main"],
        outputs=["default", "a", "b", "c", "d", "e"],
    )
    config_model = _SwitchConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        items = inputs.port("main") or [{}]
        for case in self.config.casos:
            if case.porta not in self.metadata.outputs:
                raise ValueError(
                    f"porta '{case.porta}' não existe em 'escolher' "
                    f"(use: {', '.join(self.metadata.outputs)})"
                )
            if compare(self.config.valor, case.operador, case.valor):
                context.log(f"escolher → porta '{case.porta}'")
                return NodeOutput(items={case.porta: items})
        context.log("escolher → porta 'default'")
        return NodeOutput(items={"default": items})


class _MergeConfig(BaseModel):
    modo: Literal["concatenar", "primeiro"] = "concatenar"


class MergeNode(Node):
    """Join branches back together.

    A merge runs as soon as its live inputs arrive: branches that were skipped
    resolve as dead edges, so a merge after an `if` does not hang waiting for the
    branch that never ran.
    """

    metadata = NodeMetadata(
        type="juntar", name="Juntar", category="fluxo",
        description="Reúne itens de várias entradas em uma saída.",
        inputs=["main", "b", "c"], outputs=["main"],
    )
    config_model = _MergeConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        collected: list[Any] = []
        for port in self.metadata.inputs:
            collected.extend(inputs.port(port))
        if self.config.modo == "primeiro":
            collected = collected[:1]
        return NodeOutput(items={"main": collected})


class _DelayConfig(BaseModel):
    segundos: float = Field(default=1.0, ge=0.0, le=300.0)


class DelayNode(Node):
    """Pause a branch. Bounded to 5 minutes — long waits belong to a schedule."""

    metadata = NodeMetadata(
        type="esperar", name="Esperar", category="fluxo",
        description="Aguarda alguns segundos antes de continuar.",
    )
    config_model = _DelayConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        await asyncio.sleep(self.config.segundos)
        return NodeOutput(items={"main": inputs.port("main") or [{}]})


class _StopConfig(BaseModel):
    mensagem: str = ""
    erro: bool = False


class StopNode(Node):
    """End this branch on purpose — quietly, or by failing the run."""

    metadata = NodeMetadata(
        type="parar", name="Parar", category="fluxo",
        description="Encerra o ramo. Com erro=true, derruba a execução inteira.",
        inputs=["main"], outputs=[],
    )
    config_model = _StopConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        if self.config.erro:
            raise RuntimeError(self.config.mensagem or "execução interrompida pelo nó 'parar'")
        if self.config.mensagem:
            context.log(self.config.mensagem)
        return NodeOutput()


class NoopConfig(BaseModel):
    rotulo: str = ""


class NoopNode(Node):
    """Does nothing but pass items through — useful as a join or a placeholder."""

    metadata = NodeMetadata(
        type="nada", name="Nada", category="fluxo",
        description="Passa os itens adiante sem alterar nada.",
    )
    config_model = NoopConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        return NodeOutput(items={"main": inputs.port("main") or [{}]})


CORE_NODES = [
    StartNode, SetVarsNode, IfNode, SwitchNode, MergeNode, DelayNode, StopNode, NoopNode,
]
