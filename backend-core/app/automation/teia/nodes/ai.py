"""
AI nodes — the local model, inside an automation.

Every one of these runs on the kernel's own brain (Ollama, on this machine). The
Constitution stands: a workflow can reach a cloud API through the `http` node if
the owner deliberately builds that, but the AI nodes themselves never leave the
host, so "só meu" holds by construction rather than by policy (ADR-0013 §7).
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata


def _messages(system: str, prompt: str) -> list[dict[str, str]]:
    messages = []
    if system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_json(text: str) -> Any:
    """Pull the JSON out of a model reply, fenced or not."""
    candidate = text.strip()
    if "```" in candidate:
        for block in candidate.split("```"):
            stripped = block.removeprefix("json").strip()
            if stripped.startswith(("{", "[")):
                candidate = stripped
                break
    try:
        return json.loads(candidate)
    except ValueError:
        pass
    starts = [i for i in (candidate.find("{"), candidate.find("[")) if i >= 0]
    end = max(candidate.rfind("}"), candidate.rfind("]"))
    if starts and end > min(starts):
        try:
            return json.loads(candidate[min(starts) : end + 1])
        except ValueError:
            pass
    raise ValueError(f"o modelo não devolveu JSON válido: {text[:200]}")


class _PromptConfig(BaseModel):
    prompt: str = Field(..., min_length=1)
    sistema: str = ""
    temperatura: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)


class LlmPromptNode(Node):
    """Ask the local model something. Emits `{resposta}`."""

    metadata = NodeMetadata(
        type="ia_perguntar", name="Perguntar à IA", category="ia",
        description="Envia um prompt ao cérebro local (Ollama) e emite a resposta.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _PromptConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        brain = context.services.require("brain")
        cfg = self.config
        answer = await brain.chat(
            _messages(cfg.sistema, cfg.prompt),
            temperature=cfg.temperatura,
            max_tokens=cfg.max_tokens,
        )
        context.log(f"ia_perguntar: {len(answer)} caractere(s) de resposta")
        return NodeOutput.single({"resposta": answer, "prompt": cfg.prompt})


class _JsonPromptConfig(BaseModel):
    prompt: str = Field(..., min_length=1)
    formato: str = Field(
        default="", description="descrição do JSON esperado, ex.: {\"titulo\": \"...\"}"
    )
    sistema: str = ""
    temperatura: float | None = Field(default=0.1, ge=0.0, le=2.0)


class LlmJsonNode(Node):
    """Ask the local model for structured data and parse it.

    Small local models drift out of JSON easily, so this asks strictly, parses
    tolerantly, and fails loudly when the reply really isn't JSON — a wrong shape
    should stop the automation, not flow downstream as garbage.
    """

    metadata = NodeMetadata(
        type="ia_json", name="IA estruturada", category="ia",
        description="Pede um JSON ao cérebro local e devolve o objeto já lido.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _JsonPromptConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        brain = context.services.require("brain")
        cfg = self.config
        instruction = (
            "Responda EXCLUSIVAMENTE com JSON válido, sem comentários e sem texto ao redor."
        )
        if cfg.formato:
            instruction += f"\nFormato esperado: {cfg.formato}"
        system = f"{cfg.sistema}\n{instruction}".strip()

        reply = await brain.chat(_messages(system, cfg.prompt), temperature=cfg.temperatura)
        data = _extract_json(reply)
        return NodeOutput.single(data if isinstance(data, dict) else {"dados": data})


class _SummarizeConfig(BaseModel):
    texto: str = Field(..., min_length=1)
    instrucao: str = "Resuma em português, de forma direta e útil."
    max_palavras: int = Field(default=120, ge=10, le=2000)


class LlmSummarizeNode(Node):
    """Summarise text with the local model. Emits `{resumo}`."""

    metadata = NodeMetadata(
        type="ia_resumir", name="Resumir com IA", category="ia",
        description="Resume um texto usando o cérebro local.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _SummarizeConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        brain = context.services.require("brain")
        cfg = self.config
        prompt = (
            f"{cfg.instrucao}\nUse no máximo {cfg.max_palavras} palavras.\n\n"
            f"---\n{cfg.texto}\n---"
        )
        summary = await brain.chat(
            _messages("Você resume com precisão, sem inventar nada.", prompt),
            temperature=0.2,
        )
        return NodeOutput.single({"resumo": summary.strip()})


AI_NODES = [LlmPromptNode, LlmJsonNode, LlmSummarizeNode]
