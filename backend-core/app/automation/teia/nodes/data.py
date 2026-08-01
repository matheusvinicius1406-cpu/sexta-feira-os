"""
Data nodes — shaping what flows between the others.

Text templates, JSON, filtering, sorting, field picking and aggregation. All of
it operates on the list of items at the `main` input port.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata
from app.automation.teia.nodes.core import compare


def _field(item: Any, path: str) -> Any:
    """Read `a.b.c` out of an item, tolerating missing pieces."""
    current = item
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, (list, tuple)) and segment.lstrip("-").isdigit():
            index = int(segment)
            current = current[index] if -len(current) <= index < len(current) else None
        else:
            return None
    return current


class _TemplateConfig(BaseModel):
    texto: str = ""
    campo: str = "texto"


class TemplateNode(Node):
    """Render one piece of text (already expression-resolved) into an item.

    This is how a workflow builds the sentence it will remember, notify or feed to
    the local model: `texto` holds the `{{ ... }}` and comes out under `campo`.
    """

    metadata = NodeMetadata(
        type="texto", name="Texto", category="dados",
        description="Monta um texto a partir de expressões e emite {campo: texto}.",
    )
    config_model = _TemplateConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        return NodeOutput.single({self.config.campo: self.config.texto})


class _JsonParseConfig(BaseModel):
    texto: str = ""
    tolerante: bool = True


class JsonParseNode(Node):
    """Parse JSON text into a real item.

    `tolerante` also accepts JSON wrapped in prose or a ```json fence, which is
    exactly what a local model tends to return.
    """

    metadata = NodeMetadata(
        type="json_ler", name="Ler JSON", category="dados",
        description="Converte texto JSON em item estruturado.",
    )
    config_model = _JsonParseConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        raw = (self.config.texto or "").strip()
        try:
            return NodeOutput.single(json.loads(raw))
        except ValueError:
            if not self.config.tolerante:
                raise ValueError("o texto não é JSON válido") from None

        candidate = raw
        if "```" in candidate:
            blocks = candidate.split("```")
            for block in blocks:
                stripped = block.removeprefix("json").strip()
                if stripped.startswith(("{", "[")):
                    candidate = stripped
                    break
        start = min(
            (i for i in (candidate.find("{"), candidate.find("[")) if i >= 0),
            default=-1,
        )
        end = max(candidate.rfind("}"), candidate.rfind("]"))
        if start >= 0 and end > start:
            try:
                return NodeOutput.single(json.loads(candidate[start : end + 1]))
            except ValueError:
                pass
        raise ValueError("não encontrei JSON válido no texto")


class _FilterConfig(BaseModel):
    campo: str = ""
    operador: str = "nao_vazio"
    valor: Any = None


class FilterNode(Node):
    """Keep only the items whose `campo` satisfies the condition."""

    metadata = NodeMetadata(
        type="filtrar", name="Filtrar", category="dados",
        description="Mantém só os itens que passam na condição.",
    )
    config_model = _FilterConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        kept = [
            item for item in inputs.port("main")
            if compare(_field(item, self.config.campo), self.config.operador, self.config.valor)
        ]
        context.log(f"filtrar: {len(kept)} de {len(inputs.port('main'))} item(ns)")
        return NodeOutput(items={"main": kept})


class _PickConfig(BaseModel):
    campos: dict[str, str] = Field(default_factory=dict)   # destino -> caminho de origem


class PickNode(Node):
    """Reshape each item: `{novo_nome: caminho.na.origem}`."""

    metadata = NodeMetadata(
        type="mapear", name="Mapear campos", category="dados",
        description="Reescreve cada item escolhendo e renomeando campos.",
    )
    config_model = _PickConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        mapped = [
            {dest: _field(item, src) for dest, src in self.config.campos.items()}
            for item in inputs.port("main")
        ]
        return NodeOutput(items={"main": mapped})


class _SortConfig(BaseModel):
    campo: str = ""
    decrescente: bool = False


class SortNode(Node):
    """Sort items by a field (missing values sort last)."""

    metadata = NodeMetadata(
        type="ordenar", name="Ordenar", category="dados",
        description="Ordena os itens por um campo.",
    )
    config_model = _SortConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        def key(item: Any) -> tuple[int, str]:
            value = _field(item, self.config.campo)
            return (1, "") if value is None else (0, str(value))

        ordered = sorted(inputs.port("main"), key=key, reverse=self.config.decrescente)
        return NodeOutput(items={"main": ordered})


class _LimitConfig(BaseModel):
    quantidade: int = Field(default=10, ge=1, le=1000)


class LimitNode(Node):
    """Keep the first N items."""

    metadata = NodeMetadata(
        type="limitar", name="Limitar", category="dados",
        description="Mantém apenas os primeiros N itens.",
    )
    config_model = _LimitConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        return NodeOutput(items={"main": inputs.port("main")[: self.config.quantidade]})


class _AggregateConfig(BaseModel):
    operacao: Literal["contar", "somar", "media", "minimo", "maximo", "juntar"] = "contar"
    campo: str = ""
    separador: str = "\n"


class AggregateNode(Node):
    """Collapse many items into one summary item."""

    metadata = NodeMetadata(
        type="agregar", name="Agregar", category="dados",
        description="Reduz a lista a um único item (contar/somar/media/juntar...).",
    )
    config_model = _AggregateConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        items = inputs.port("main")
        operation = self.config.operacao

        if operation == "contar":
            return NodeOutput.single({"resultado": len(items), "operacao": operation})
        if operation == "juntar":
            parts = [
                str(_field(i, self.config.campo) if self.config.campo else i) for i in items
            ]
            return NodeOutput.single(
                {"resultado": self.config.separador.join(parts), "operacao": operation}
            )

        numbers: list[float] = []
        for item in items:
            raw = _field(item, self.config.campo) if self.config.campo else item
            try:
                numbers.append(float(raw))
            except (TypeError, ValueError):
                continue
        if not numbers:
            return NodeOutput.single({"resultado": 0, "operacao": operation, "itens": 0})

        value = {
            "somar": sum(numbers),
            "media": sum(numbers) / len(numbers),
            "minimo": min(numbers),
            "maximo": max(numbers),
        }[operation]
        return NodeOutput.single(
            {"resultado": value, "operacao": operation, "itens": len(numbers)}
        )


DATA_NODES = [
    TemplateNode, JsonParseNode, FilterNode, PickNode, SortNode, LimitNode, AggregateNode,
]
