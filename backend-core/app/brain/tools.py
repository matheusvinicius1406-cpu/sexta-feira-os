"""
ToolKit — what Sexta-Feira can DO on its own during a conversation.

The brain (via Ollama tool-calling) can decide to:
  * remember(content)          -> save a durable fact to the graph memory
  * recall(query)              -> search its own memory
  * run_automation(webhook,..) -> fire an n8n workflow (act in the world)

All of this happens from a plain sentence the owner speaks on the phone — no
terminal, no hand-built payloads. The tools run locally; automations bridge to
the local n8n.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger("sexta-feira.tools")


class ToolKit:
    def __init__(self, memory, automations, actions=None):
        self.memory = memory
        self.automations = automations
        self.actions = actions  # ActionService | None

    async def specs(self) -> list[dict]:
        """OpenAI/Ollama-style tool schemas. Injects live automation names as a hint."""
        automations_hint = ""
        try:
            workflows = await self.automations.list_workflows()
            names = [w["name"] for w in workflows if w.get("name")]
            if names:
                automations_hint = " Automações disponíveis: " + ", ".join(names[:30]) + "."
        except Exception as e:  # noqa: BLE001 — n8n may be off; tools still work
            logger.debug("automation list unavailable for tool specs: %s", e)

        return [
            {
                "type": "function",
                "function": {
                    "name": "remember",
                    "description": "Guarda um fato duradouro sobre o dono na memória de longo prazo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "o fato a lembrar"}
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recall",
                    "description": "Busca na memória do dono por informação relevante.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "o que procurar"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_automation",
                    "description": (
                        "Dispara uma automação (workflow do n8n) pelo caminho do seu webhook, "
                        "para AGIR no mundo (lembretes, mensagens, casa, etc.)." + automations_hint
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "webhook": {"type": "string", "description": "caminho do webhook do workflow"},
                            "payload": {"type": "object", "description": "dados para a automação"},
                        },
                        "required": ["webhook"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "device_action",
                    "description": (
                        "Manda um dispositivo do dono EXECUTAR uma ação nativa. Use para "
                        "'abrir app', 'ligar', 'navegar', etc. O 'device' é o corpo alvo "
                        "('celular', 'computador', 'carro') e 'action'/'params' descrevem o que fazer. "
                        "Ex.: action='open_app', params={'app':'whatsapp'}."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device": {"type": "string", "description": "corpo alvo: celular, computador, carro..."},
                            "action": {"type": "string", "description": "a ação nativa a executar"},
                            "params": {"type": "object", "description": "parâmetros da ação"},
                        },
                        "required": ["device", "action"],
                    },
                },
            },
        ]

    async def dispatch(self, name: str, args: dict[str, Any], db: Session, owner_id: str) -> str:
        """Execute a tool call; always returns a short human-readable result string."""
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:  # noqa: BLE001
                args = {}
        try:
            if name == "remember":
                m = await self.memory.remember(db, owner_id, args.get("content", ""), source="tool")
                return f"Memória salva: {m.content}"
            if name == "recall":
                results = await self.memory.recall_graph(db, owner_id, args.get("query", ""))
                if not results:
                    return "Nada relevante na memória."
                return "Encontrei:\n" + "\n".join(f"- {m.content}" for m in results)
            if name == "run_automation":
                out = await self.automations.trigger(args.get("webhook", ""), args.get("payload") or {})
                return "Automação disparada." if out.get("ok") else f"Falha na automação: {out.get('error', '?')}"
            if name == "device_action":
                if not self.actions:
                    return "Ações em dispositivos não estão disponíveis."
                out = await self.actions.dispatch(
                    db, owner_id, args.get("device", ""),
                    args.get("action", ""), args.get("params") or {},
                )
                if not out.get("ok"):
                    return out.get("error", "Não consegui enviar a ação.")
                dest = out.get("device", "dispositivo")
                return (
                    f"Ação enviada para {dest}."
                    if out.get("delivered")
                    else f"Ação enfileirada para {dest} (vai executar quando ele conectar)."
                )
            return f"Ferramenta desconhecida: {name}"
        except Exception as e:  # noqa: BLE001 — a tool failure must not crash the turn
            logger.warning("tool '%s' failed: %s", name, e)
            return f"Não consegui executar {name}: {e}"
