"""
Composition — one workflow calling another.

This is how the Teia does loops and reuse without cycles in a single graph: a
workflow stays a DAG, and `sub_automacao` runs another one (optionally once per
item). Nesting is bounded by `limits.max_depth`, so a workflow that calls itself
stops at a known depth instead of consuming the machine.
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata
from app.automation.teia.engine.errors import RunLimitExceeded


class _SubWorkflowConfig(BaseModel):
    automacao: str = Field(..., min_length=1, description="slug da automação a chamar")
    dados: dict = Field(default_factory=dict)
    por_item: bool = False
    falhar_se_falhar: bool = True


class SubWorkflowNode(Node):
    """Run another automation and emit its result.

    With `por_item`, it runs once per incoming item — each run receiving that item
    as its trigger payload — and the runs happen sequentially so a fan-out of
    sub-workflows can't multiply the worker pool.
    """

    metadata = NodeMetadata(
        type="sub_automacao", name="Chamar automação", category="fluxo",
        description="Executa outra automação e devolve o resultado dela.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _SubWorkflowConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        runner = context.services.require("runner")
        cfg = self.config

        if context.depth + 1 > context.limits.max_depth:
            raise RunLimitExceeded(
                f"'{cfg.automacao}': profundidade máxima de {context.limits.max_depth} "
                f"sub-automações atingida (possível recursão)"
            )

        payloads = (
            [{**cfg.dados, "item": item} for item in inputs.port("main")]
            if cfg.por_item
            else [cfg.dados]
        )
        if not payloads:
            return NodeOutput(items={"main": []})

        results = []
        for payload in payloads:
            context.cancel.raise_if_cancelled()
            result = await runner.run_slug(
                context.owner_id, cfg.automacao, payload,
                trigger_type="sub", depth=context.depth + 1,
            )
            if not result.ok and cfg.falhar_se_falhar:
                raise RuntimeError(f"sub-automação '{cfg.automacao}': {result.summary()}")
            results.append({
                "automacao": cfg.automacao,
                "ok": result.ok,
                "status": result.status.value,
                "saida": result.output,
                "resumo": result.summary(),
            })
            await asyncio.sleep(0)          # let other workers breathe between runs

        return NodeOutput(items={"main": results})


FLOW_NODES = [SubWorkflowNode]
