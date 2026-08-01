# ADR-0013: Plataforma de Automação Python-First (Teia) — substituir o n8n

> **Architecture Decision Record.** Decisão estruturante: construir uma plataforma de
> automação nativa em Python, de próxima geração, substituindo a dependência do n8n
> (Node.js). Ver `../architecture/AUTOMATION_PLATFORM.md`, `../architecture/API_ECOSYSTEM.md`
> e `../agents/N8N_ORCHESTRATOR.md`.

- **Número:** 0013
- **Título:** Adotar arquitetura Python-First para a plataforma de automação (Teia)
- **Data:** 2026-07-20
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (atuando como Arquiteto de Software Sênior)
- **Aprovado por:** Proprietário ("aprovado, comece a fase 1")
- **Documentos afetados:** `../architecture/API_ECOSYSTEM.md`, `../agents/N8N_ORCHESTRATOR.md`,
  `../architecture/NORTH_STAR.md`

## Contexto

A automação hoje depende do **n8n** (Node.js), integrado como "as mãos" do kernel. O
proprietário definiu a filosofia **Python-First**: Python deve ser a linguagem nativa e de
primeira classe de **toda** a lógica de automação (workflows, nodes, triggers, engine,
plugins, integrações), aproveitando ao máximo o ecossistema Python. O objetivo é uma
plataforma que compita com n8n/Zapier/Make **sem** limitações comerciais e **sem** depender
de um runtime Node.js.

## Problema

Como projetar uma plataforma de automação nativa em Python — extensível, performática,
com IA nativa, durável e observável — que substitua o n8n, se integre ao kernel existente e
**não** viole "só meu"?

## Decisão

Adotar a arquitetura descrita em `../architecture/AUTOMATION_PLATFORM.md` (codinome **Teia**):

1. **Workflow como objeto Python** (grafo de nodes), serializável (JSON/YAML), construível por
   código/arquivo/API/CLI/visual/agendamento; o motor nunca depende da UI.
2. **Node, Trigger, Connector, Engine, Plugin — tudo classe/pacote Python.** I/O tipado com
   Pydantic v2; execução assíncrona (asyncio).
3. **Engine em Python** com execução assíncrona/paralela, filas atrás de contrato (in-process
   → arq/Redis), retries, timeout, checkpoints, compensação (saga), persistência (SQLAlchemy),
   logs (structlog), tracing (OpenTelemetry), eventos/hooks.
4. **Plugins como pacotes Python** com descoberta por entry points; isolamento para plugins
   não confiáveis.
5. **Clean Architecture / DDD / SOLID**, tipagem completa, pytest (unit + integração).
6. **Reuso do kernel:** cofre Fernet (credenciais), EventBus (triggers de evento), Scheduler.
7. **Bibliotecas maduras antes de implementação própria** (FastAPI, SQLAlchemy, HTTPX,
   APScheduler, arq, Typer, watchdog, boto3, Playwright, etc.).

### Preservação dos princípios invioláveis

- **"só meu":** node de IA de nuvem é **capacidade explícita do dono** (default Ollama local;
  nuvem exige cofre + confirmação, auditável) — a cognição do Kernel permanece local. A
  plataforma não abre a mente do JARVIS para a nuvem.
- **Kernel independente do modelo** e **substituibilidade**: a Teia é subsistema modular; o
  n8n vira conector legado, não é dependência dura.
- **Segurança nativa:** plugins do dono por padrão; isolamento para não confiáveis; segredos
  nunca no JSON do workflow.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Plataforma Python-First nativa (escolhida)** | controle total, IA nativa, "só meu", mesmo idioma do kernel | esforço grande; construir a engine | — (mitigado por plano incremental) |
| Continuar dependente do n8n (Node.js) | pronto | runtime Node.js; extensões em JS/TS; limita Python-First; menos controle | rejeitada (contraria a filosofia) |
| Fork do n8n adaptado | reusa UI/nodes | base TypeScript/Node; reescrever em Python = fork inviável | rejeitada |
| Usar só uma lib de workflow existente (Prefect/Airflow/Dagster) | maduro | orientado a *data pipelines*, não a automação/integrações com UI e triggers de app; pesado; modelo diferente | rejeitada como base (podem inspirar; conectores possíveis) |

## Consequências

- **Positivas:** automação 100% Python, extensível, IA nativa, sob "só meu"; unifica o stack;
  remove a dependência de runtime Node.js.
- **Custos:** construir a engine e o ecossistema de nodes é trabalho substancial (por isso o
  plano incremental de 10 fases, cada uma um PR).
- **Neutras:** o n8n continua disponível como conector durante a migração.

## Riscos e mitigação

Detalhados em `../architecture/AUTOMATION_PLATFORM.md` §11 (R1–R9). Destaques: escopo (fatias
finas), segurança de plugins (isolamento), "rollback" honesto como compensação, cloud IA sob
consentimento explícito.

## Plano

10 fases incrementais (AUTOMATION_PLATFORM.md §12), começando pelo **núcleo de domínio** sem
execução.

## Estado da implementação (2026-08-01)

Fases 0, 1, 2, 3, 5, 6 e 10 entregues; 8 parcial. O **n8n foi removido**: não há mais
`N8nClient`, bridge de callback, workflows JSON, servidor MCP nem serviço no
`docker-compose`. O que existe hoje:

| Peça | Onde | O que faz |
|---|---|---|
| Domínio | `automation/teia/domain/` | grafo, contratos de node/trigger, validação |
| Orquestrador | `engine/orchestrator.py` | prontidão dos nós, roteamento, poda de ramos, guardas |
| Operários | `engine/workers.py` | executam um nó cada: resolução, validação, retry, timeout |
| Expressões | `engine/expressions.py` | `{{ }}` por busca de caminho — sem `eval`, sem código |
| Persistência | `store.py` + migração `a1c7d2f4b8e0` | workflows, execuções, checkpoint por nó |
| Gatilhos | `triggers/` | cron próprio, intervalo, evento (EventBus), webhook, manual |
| Nodes | `nodes/` | 44 tipos: fluxo, dados, HTTP, IA local, kernel, arquivos, sistema |
| Catálogo | `catalog.py` | 10 automações prontas, só com capacidades locais |
| Interfaces | `api/routers/automation.py`, `cli.py` | REST + CLI sobre o mesmo objeto |

**Pendentes:** plugins por entry point (Fase 4), broker distribuído (Fase 7), RAG/agente/MCP
nos nodes de IA (resto da Fase 8), OpenTelemetry (Fase 9).

### Decisões tomadas na implementação

- **Cron próprio em vez de `croniter`.** ~100 linhas de aritmética pura, testadas, contra uma
  dependência nova num kernel deliberadamente enxuto. A regra "biblioteca madura primeiro"
  vale para não reescrever um motor — não para casar um horário.
- **CLI com `argparse` em vez de Typer.** A ferramenta que precisa funcionar quando nada mais
  está de pé não deve depender de um pacote a mais.
- **Sem laços no grafo.** O workflow continua um DAG; repetição e reuso vêm do node
  `sub_automacao`, com profundidade limitada — o que também mata a recursão infinita.
- **Validação estática pula config com `{{ }}`.** O tipo real de um placeholder só existe em
  execução; quem valida é o operário, no momento em que a resposta existe.
- **O cérebro executa, o dono autoria.** `ToolKit` roda automações existentes mas não cria
  nem edita nenhuma, então um prompt envenenado só alcança o que o dono já aprovou.
