"""
ToolKit — what Sexta-Feira can DO on its own during a conversation.

The brain (via Ollama tool-calling) can decide to:
  * remember(content)          -> save a durable fact to the graph memory
  * recall(query)              -> search its own memory
  * run_automation(name, ..)   -> run a Teia automation (act in the world)
  * list_automations(query)    -> see what automations exist
  * automation_history(name)   -> check how the last runs went

All of this happens from a plain sentence the owner speaks on the phone — no
terminal, no hand-built payloads. Everything runs locally, in this process.

The brain can RUN an automation the owner already has; it cannot write a new one
or change one. Authoring stays with the owner (the API and the CLI), so a
poisoned prompt can only reach behaviours the owner already approved.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.automation.teia.engine.errors import WorkflowNotFound
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.tools")


def _compute_due(args: dict) -> datetime | None:
    """Turn {at} ISO or {in_seconds|in_minutes|in_hours|in_days} into a UTC datetime."""
    if args.get("at"):
        try:
            dt = datetime.fromisoformat(str(args["at"]).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    now = datetime.now(UTC)
    for unit, mult in (("in_seconds", 1), ("in_minutes", 60), ("in_hours", 3600), ("in_days", 86400)):
        if args.get(unit) is not None:
            try:
                return now + timedelta(seconds=float(args[unit]) * mult)
            except (TypeError, ValueError):
                return None
    return None


class ToolKit:
    def __init__(self, memory, automations, actions=None, scheduler=None,
                 connectors=None, world=None, planning=None, decision=None, learning=None,
                 briefing=None, vision=None, web_search=None, attachments=None):
        self.memory = memory
        self.automations = automations
        self.actions = actions        # ActionService | None
        self.scheduler = scheduler    # Scheduler | None
        self.connectors = connectors  # ConnectorService | None
        self.world = world            # WorldModel | None — the present + owner model
        self.planning = planning      # PlanningEngine | None — goals + decomposition
        self.decision = decision      # DecisionEngine | None — choose under constraints
        self.learning = learning      # LearningEngine | None — observe → learn → adapt
        self.briefing = briefing      # BriefingService | None — the daily report
        self.vision = vision          # VisionEngine | None — enxergar o mundo
        self.web_search = web_search  # WebSearch | None — acesso à internet
        self.attachments = attachments  # AttachmentAnalyzer | None — analisar arquivos
        self.subagents = None         # SubAgentRunner | None (wired after construction)
        self.directors = None         # DirectorService | None (wired after construction)

    async def specs_subset(self, allowed: list[str]) -> list[dict]:
        """The tool specs restricted to `allowed` names — used for sub-agents."""
        return [s for s in await self.specs() if s["function"]["name"] in allowed]

    def _automation_names(self) -> list[str]:
        """The owner's enabled automation slugs — used to hint the model."""
        if not self.automations:
            return []
        db = self.automations.session_factory()
        try:
            owner = db.query(Owner).first()
            if not owner:
                return []
            return [
                row.slug
                for row in self.automations.store.list(db, owner.id, enabled_only=True)
            ]
        finally:
            db.close()

    async def specs(self) -> list[dict]:
        """OpenAI/Ollama-style tool schemas. Injects live automation names as a hint."""
        automations_hint = ""
        try:
            names = self._automation_names()
            if names:
                automations_hint = " Automações disponíveis: " + ", ".join(names[:30]) + "."
        except Exception as e:  # noqa: BLE001 — listing must never break tool specs
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
                        "Executa uma automação da Teia pelo nome (slug) para AGIR no mundo: "
                        "briefing, backup, avisos, captura, etc. Use 'list_automations' antes "
                        "se não souber o nome exato." + automations_hint
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "slug da automação, ex.: briefing-matinal"},
                            "payload": {"type": "object", "description": "dados de entrada da automação"},
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_automations",
                    "description": (
                        "Lista as automações do dono, com o que cada uma faz e se está ativa."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "filtro opcional por nome/descrição"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "automation_history",
                    "description": (
                        "Mostra como foram as últimas execuções de uma automação "
                        "(status, duração, erro). Use para responder 'o backup rodou?'."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "slug da automação"},
                        },
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
            {
                "type": "function",
                "function": {
                    "name": "schedule_reminder",
                    "description": (
                        "Agenda um lembrete para o futuro ('me lembra disso amanhã / daqui a 2 meses'). "
                        "Informe o tempo por 'in_minutes'/'in_hours'/'in_days' OU 'at' (ISO 8601)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "o que lembrar"},
                            "in_minutes": {"type": "number"},
                            "in_hours": {"type": "number"},
                            "in_days": {"type": "number"},
                            "at": {"type": "string", "description": "data/hora ISO 8601"},
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "schedule_action",
                    "description": (
                        "Agenda uma AÇÃO em um dispositivo para um horário futuro "
                        "(ex.: navegar para a faculdade às 8h). Tempo como no schedule_reminder."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device": {"type": "string"},
                            "action": {"type": "string"},
                            "params": {"type": "object"},
                            "in_minutes": {"type": "number"},
                            "in_hours": {"type": "number"},
                            "in_days": {"type": "number"},
                            "at": {"type": "string"},
                        },
                        "required": ["device", "action"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_capabilities",
                    "description": (
                        "Lista as capacidades de API disponíveis (buscáveis) que você pode "
                        "chamar para consultar/agir no mundo. Use ANTES de call_api para "
                        "descobrir o nome e os parâmetros certos."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "filtro opcional"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "call_api",
                    "description": (
                        "Executa uma capacidade de API definida pelo dono, pelo nome "
                        "(descubra com list_capabilities). Passe 'params' conforme o schema dela."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "capability": {"type": "string", "description": "nome da capacidade"},
                            "params": {"type": "object", "description": "parâmetros da chamada"},
                        },
                        "required": ["capability"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_goal",
                    "description": (
                        "Cria um OBJETIVO no motor de planejamento (o sistema trabalha por "
                        "objetivos). Use para metas do dono. 'priority' maior = mais importante."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "o objetivo"},
                            "description": {"type": "string"},
                            "priority": {"type": "number", "description": "prioridade (1-5, maior = mais)"},
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "decompose_goal",
                    "description": (
                        "Divide um objetivo grande em subtarefas (sub-objetivos filhos). "
                        "Passe 'goal_id' e a lista 'subtasks'. O progresso do pai é a média dos filhos."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {"type": "string"},
                            "subtasks": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["goal_id", "subtasks"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_goals",
                    "description": "Lista os objetivos do dono (por prioridade). Filtro opcional por status.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "description": "pending|active|blocked|done|cancelled"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "sprint_board",
                    "description": (
                        "Mostra o quadro (board) dos objetivos por coluna: backlog, fazendo, "
                        "bloqueado e concluído — a visão de sprint. Sem argumentos."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_goal",
                    "description": (
                        "Marca um objetivo como concluído (progresso 100%). Desbloqueia objetivos "
                        "que dependiam dele. Passe 'goal_id'."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"goal_id": {"type": "string"}},
                        "required": ["goal_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "daily_briefing",
                    "description": (
                        "Gera um briefing agora: resume o estado atual, os objetivos, o foco "
                        "sugerido, eventos recentes e aprendizados — o 'reporte' do segundo "
                        "cérebro. Sem argumentos."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "record_learning",
                    "description": (
                        "Registra um aprendizado depois de uma ação/resultado (ciclo de "
                        "aprendizado contínuo). 'quality' de 0.0 (ruim) a 1.0 (ótimo); 'lesson' "
                        "é a lição durável (vai para a memória); 'tag' agrupa o tema."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "context": {"type": "string", "description": "o que foi tentado/aconteceu"},
                            "observation": {"type": "string", "description": "o resultado observado"},
                            "quality": {"type": "number", "description": "0.0 a 1.0"},
                            "lesson": {"type": "string", "description": "a lição durável a lembrar"},
                            "tag": {"type": "string", "description": "tema (para detectar recorrência)"},
                        },
                        "required": ["context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recall_lessons",
                    "description": "Lista os aprendizados recentes (opcionalmente por 'tag').",
                    "parameters": {
                        "type": "object",
                        "properties": {"tag": {"type": "string"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "decide_next",
                    "description": (
                        "Pergunta ao motor de decisão QUAL objetivo focar agora. Ele pondera "
                        "prioridade, prazo e andamento (e adapta à energia inferida do dono), "
                        "escolhe de forma determinística e explica o porquê. Sem argumentos."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remember_context",
                    "description": (
                        "Atualiza o estado do AGORA (World Model): um fato do presente por "
                        "chave (ex.: key='foco_atual', value='estudando cálculo'). Use para "
                        "localização, foco, trabalho ativo, objetivos correntes. Marque "
                        "is_inference=true quando for inferência (humor/energia)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "nome canônico do fato do presente"},
                            "value": {"type": "string", "description": "o valor atual"},
                            "category": {
                                "type": "string",
                                "description": "environment|user_state|active_work|goals|context|capabilities|other",
                            },
                            "is_inference": {"type": "boolean", "description": "true se for inferido, não observado"},
                        },
                        "required": ["key", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remember_about_me",
                    "description": (
                        "Atualiza o modelo do DONO ao longo do tempo (User Model): um traço "
                        "durável por chave (ex.: key='estilo_programacao', value='prefere "
                        "Python, tipado'). Use para objetivos, hábitos, preferências, estilo, "
                        "projetos. Diferente de 'remember', que guarda um fato solto."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "nome canônico do traço do dono"},
                            "value": {"type": "string", "description": "o valor do traço"},
                            "category": {
                                "type": "string",
                                "description": "goals|habits|preferences|style|knowledge|social|projects|other",
                            },
                        },
                        "required": ["key", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate",
                    "description": (
                        "Delega uma sub-tarefa focada a um sub-agente especialista (que roda "
                        "localmente e devolve um resultado). Use para pesquisa/planejamento "
                        "que valha isolar. Ex.: role='pesquisador', task='resuma X da memória'."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "description": "o papel do sub-agente"},
                            "task": {"type": "string", "description": "a tarefa a delegar"},
                        },
                        "required": ["role", "task"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "consult_director",
                    "description": (
                        "Delega uma tarefa a um DIRETOR permanente — especialista que acumula "
                        "expertise entre conversas (engenharia, pesquisa, seguranca, memoria, "
                        "automacao, aprendizagem, dispositivos). Prefira ao 'delegate' quando "
                        "o domínio casa com um diretor."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "director": {"type": "string", "description": "nome do diretor (ex.: engenharia)"},
                            "task": {"type": "string", "description": "a tarefa a delegar"},
                        },
                        "required": ["director", "task"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_image",
                    "description": (
                        "Analisa uma imagem usando o modelo de visão local (llava). "
                        "Descreve o que vê, lê texto (OCR), identifica objetos. "
                        "Útil para: câmera, fotos, screenshots, documentos."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_base64": {"type": "string", "description": "imagem em base64"},
                            "prompt": {"type": "string", "description": "pergunta/instrução sobre a imagem"},
                        },
                        "required": ["image_base64"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": (
                        "Busca informações na internet via DuckDuckGo. "
                        "Use para: notícias, previsão do tempo, cotações, dúvidas, pesquisas."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "o que buscar na internet"},
                            "max_results": {"type": "number", "description": "máximo de resultados (padrão 5)"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_page",
                    "description": (
                        "Baixa e extrai o conteúdo de uma página web. "
                        "Use quando precisar do conteúdo completo de um link."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL da página"},
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": (
                        "Toca música ou rádio. Busca no YouTube ou em estações de rádio. "
                        "Filtro de anúncios automático. Ex.: 'toque jazz', 'rádio sertanejo', "
                        "'toca Bohemian Rhapsody'."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "nome da música, artista ou gênero"},
                            "source": {"type": "string", "description": "radio, youtube, ou auto"},
                        },
                        "required": ["query"],
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
                if not self.automations:
                    return "Automações indisponíveis."
                slug = (args.get("name") or args.get("automacao") or args.get("webhook") or "").strip()
                if not slug:
                    return "Diga qual automação executar (use 'list_automations')."
                try:
                    result = await self.automations.run_slug(
                        owner_id, slug, args.get("payload") or {}
                    )
                except WorkflowNotFound as e:
                    return str(e)
                return result.summary()
            if name == "list_automations":
                if not self.automations:
                    return "Automações indisponíveis."
                rows = self.automations.list(db, owner_id, query=args.get("query"))
                if not rows:
                    return "Nenhuma automação cadastrada ainda."
                return "Automações:\n" + "\n".join(
                    f"- {r['slug']}{'' if r['enabled'] else ' (desativada)'}: "
                    f"{r['description'] or r['name']}"
                    for r in rows[:40]
                )
            if name == "automation_history":
                if not self.automations:
                    return "Automações indisponíveis."
                runs = self.automations.executions.list(
                    db, owner_id, slug=(args.get("name") or "").strip() or None, limit=10
                )
                if not runs:
                    return "Nenhuma execução registrada ainda."
                return "Últimas execuções:\n" + "\n".join(
                    f"- {r.workflow_slug} [{r.status}] {r.duration_ms or 0} ms"
                    + (f" — {r.error}" if r.error else "")
                    for r in runs
                )
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
            if name == "schedule_reminder":
                if not self.scheduler:
                    return "Agendamento não disponível."
                due = _compute_due(args)
                if not due:
                    return "Não entendi para quando; me diga em minutos/horas/dias ou uma data."
                self.scheduler.schedule(
                    db, owner_id, kind="reminder", due_at=due,
                    text=args.get("text", ""), device=args.get("device"),
                )
                return f"Lembrete agendado para {due.isoformat(timespec='minutes')}."
            if name == "schedule_action":
                if not self.scheduler:
                    return "Agendamento não disponível."
                due = _compute_due(args)
                if not due:
                    return "Não entendi para quando; me diga em minutos/horas/dias ou uma data."
                self.scheduler.schedule(
                    db, owner_id, kind="action", due_at=due,
                    device=args.get("device"), action=args.get("action", ""),
                    params=args.get("params") or {},
                )
                return f"Ação agendada para {due.isoformat(timespec='minutes')}."
            if name == "list_capabilities":
                if not self.connectors:
                    return "Conectores indisponíveis."
                caps = self.connectors.list_capabilities(db, owner_id, args.get("query"))
                if not caps:
                    return "Nenhuma capacidade de API cadastrada ainda."
                return "Capacidades disponíveis:\n" + "\n".join(
                    f"- {c['name']}: {c['description']}" for c in caps[:40]
                )
            if name == "call_api":
                if not self.connectors:
                    return "Conectores indisponíveis."
                out = await self.connectors.invoke(
                    db, owner_id, args.get("capability", ""), args.get("params") or {}
                )
                if not out.get("ok"):
                    return f"Falha na API: {out.get('error') or out.get('status')}"
                data = out.get("data")
                text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
                return f"Resultado ({out.get('status')}): {text[:1500]}"
            if name == "create_goal":
                if not self.planning:
                    return "Planejamento indisponível."
                g = await self.planning.create_goal(
                    db, owner_id, args.get("title", ""),
                    description=args.get("description"),
                    priority=int(args.get("priority", 2) or 2),
                )
                return f"Objetivo criado: {g.title} (id {g.id})"
            if name == "decompose_goal":
                if not self.planning:
                    return "Planejamento indisponível."
                subs = args.get("subtasks") or []
                if isinstance(subs, str):
                    subs = [subs]
                children = await self.planning.decompose(
                    db, owner_id, args.get("goal_id", ""), list(subs)
                )
                return f"Objetivo dividido em {len(children)} subtarefas."
            if name == "list_goals":
                if not self.planning:
                    return "Planejamento indisponível."
                goals = self.planning.list_goals(db, owner_id, args.get("status"))
                if not goals:
                    return "Nenhum objetivo."
                return "Objetivos:\n" + "\n".join(
                    f"- [{g.status}] {g.title} ({int(g.progress * 100)}%) id={g.id}"
                    for g in goals[:40]
                )
            if name == "complete_goal":
                if not self.planning:
                    return "Planejamento indisponível."
                g = await self.planning.complete(db, owner_id, args.get("goal_id", ""))
                return f"Objetivo concluído: {g.title}" if g else "Objetivo não encontrado."
            if name == "sprint_board":
                if not self.planning:
                    return "Planejamento indisponível."
                board = self.planning.board(db, owner_id)
                labels = {"backlog": "Backlog", "doing": "Fazendo",
                          "blocked": "Bloqueado", "done": "Concluído"}
                lines = []
                for col, label in labels.items():
                    items = board["columns"][col]
                    lines.append(f"{label} ({len(items)}):")
                    lines.extend(f"  - {i['title']} ({int(i['progress'] * 100)}%)" for i in items[:10])
                return "\n".join(lines) or "Quadro vazio."
            if name == "daily_briefing":
                if not self.briefing:
                    return "Briefing indisponível."
                b = await self.briefing.generate(db, owner_id, kind="on_demand")
                return b.summary
            if name == "record_learning":
                if not self.learning:
                    return "Aprendizado indisponível."
                entry = await self.learning.record(
                    db, owner_id, args.get("context", ""),
                    observation=args.get("observation"),
                    quality=float(args.get("quality", 0.5) or 0.5),
                    lesson=args.get("lesson"), tag=args.get("tag"), source="tool",
                )
                return f"Aprendizado registrado (qualidade {entry.quality})."
            if name == "recall_lessons":
                if not self.learning:
                    return "Aprendizado indisponível."
                rows = self.learning.lessons(db, owner_id, tag=args.get("tag"))
                if not rows:
                    return "Nenhum aprendizado ainda."
                return "Aprendizados:\n" + "\n".join(
                    f"- {r.lesson or r.context} (q={r.quality})" for r in rows[:30]
                )
            if name == "decide_next":
                if not self.decision:
                    return "Motor de decisão indisponível."
                d = await self.decision.decide_next_goal(db, owner_id)
                if not d:
                    return "Nenhum objetivo elegível para focar agora."
                return f"Focar em: {d.chosen_label}. {d.rationale}"
            if name == "remember_context":
                if not self.world:
                    return "World Model indisponível."
                f = self.world.set_fact(
                    db, owner_id, args.get("key", ""), args.get("value", ""),
                    category=args.get("category", "other"), source="tool",
                    is_inference=bool(args.get("is_inference", False)),
                )
                return f"Estado atualizado: {f.key} = {f.value}"
            if name == "remember_about_me":
                if not self.world:
                    return "User Model indisponível."
                a = self.world.set_attribute(
                    db, owner_id, args.get("key", ""), args.get("value", ""),
                    category=args.get("category", "other"), source="tool",
                )
                return f"Anotado sobre você: {a.key} = {a.value}"
            if name == "delegate":
                if not self.subagents:
                    return "Sub-agentes indisponíveis."
                result = await self.subagents.run(
                    db, owner_id, args.get("role", "assistente"), args.get("task", "")
                )
                return f"Sub-agente ({args.get('role', 'assistente')}): {result[:1500]}"
            if name == "consult_director":
                if not self.directors:
                    return "Diretores indisponíveis."
                result = await self.directors.delegate(
                    db, owner_id, args.get("director", ""), args.get("task", "")
                )
                return f"Diretor ({args.get('director', '?')}): {result[:1500]}"
            if name == "analyze_image":
                if not self.vision:
                    from app.core.config import settings
                    return (
                        f"Visão indisponível. Rode: ollama pull "
                        f"{settings.vision_model_resolved}"
                    )
                result = await self.vision.analyze_image(
                    args.get("image_base64", ""),
                    args.get("prompt", "Descreva esta imagem.")
                )
                return f"Análise: {result[:2000]}"
            if name == "web_search":
                if not self.web_search:
                    return "Busca web indisponível."
                results = await self.web_search.search(
                    args.get("query", ""),
                    max_results=int(args.get("max_results", 5) or 5)
                )
                if not results:
                    return "Nenhum resultado encontrado."
                lines = [f"- {r.title}: {r.snippet}\n  {r.url}" for r in results]
                return "Resultados da busca:\n" + "\n".join(lines)
            if name == "fetch_page":
                if not self.web_search:
                    return "Busca web indisponível."
                result = await self.web_search.fetch_page(args.get("url", ""))
                if not result.get("success"):
                    return f"Falha ao acessar {args.get('url', '?')}: {result.get('error', '?')}"
                content = result.get("content", "")[:2000]
                return f"📄 {result.get('title', '')}\n\n{content}"
            if name == "play_music":
                # Radio integration — search and return playable tracks
                try:
                    from app.api.routers.radio import get_radio
                    radio = get_radio()
                    search_result = await radio.play_search(
                        args.get("query", ""),
                        source=args.get("source", "auto")
                    )
                    tracks = search_result.get("tracks", [])
                    if not tracks:
                        return "Nenhuma música/estação encontrada."
                    lines = []
                    for t in tracks[:5]:
                        lines.append(f"🎵 {t['title']} — {t.get('artist', '')} [{t['stream_type']}]")
                    return f"Encontrei {len(tracks)} opções:\n" + "\n".join(lines)
                except Exception as e:
                    return f"Erro ao buscar música: {e}"
            return f"Ferramenta desconhecida: {name}"
        except Exception as e:  # noqa: BLE001 — a tool failure must not crash the turn
            logger.warning("tool '%s' failed: %s", name, e)
            return f"Não consegui executar {name}: {e}"
