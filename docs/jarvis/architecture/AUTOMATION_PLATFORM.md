# Plataforma de Automação — Arquitetura Python-First ("Teia")

> **Proposta de arquitetura** (Fase 0 — nenhum código ainda). A plataforma de automação
> nativa em Python que substitui a dependência do n8n (Node.js) e realiza a **Automation
> API** do `NORTH_STAR.md` de forma "só meu". Codinome de trabalho: **Teia** (a teia de
> automações). Estado: `[FUTURO]` — este documento define o alvo; ver **ADR-0013**.

## 1. Visão e posicionamento

Não é um clone do n8n. É uma **plataforma de automação de próxima geração onde Python é a
linguagem de primeira classe e nativa de toda a lógica de execução** — workflows, nodes,
triggers, engine, plugins e integrações são todos Python. A interface visual é apenas **uma**
forma de construir workflows; o motor **nunca** depende dela.

**Como se encaixa no projeto:** hoje o kernel usa o n8n (Node.js) como "as mãos". A Teia
passa a ser a Automation API nativa — mesmo idioma do kernel (Python/FastAPI/SQLAlchemy),
reusa o **cofre de credenciais (Fernet)**, o **EventBus** (como fonte de triggers) e o
**Scheduler**. O n8n permanece suportado como *conector legado* durante a migração, sem ser
dependência dura.

**Princípio inviolável preservado ("só meu"):** a plataforma **suporta** provedores de IA de
nuvem, mas apenas como **capacidades que o dono configura explicitamente** por workflow
(igual a "enviar e-mail" alcança o Gmail) — nunca a cognição autônoma do Kernel vazando para
a nuvem. A distinção é registrada na §7 e no ADR-0013.

## 2. As abstrações centrais

### 2.1 Workflow — um objeto Python
Um **grafo dirigido** de `Node`s ligados por `Connection`s. Representado internamente como
objeto Python (domínio puro), **serializável** para JSON/YAML e **construível** por:
código Python · arquivo · API REST · CLI · editor visual · agendamento. O motor opera sobre
o grafo de objetos, jamais sobre a UI.

```python
wf = Workflow(name="briefing-matinal")
gatilho = wf.add(ScheduleTrigger(cron="0 7 * * *"))
dados   = wf.add(HttpRequestNode(url="{secret:API}/status"))
resumo  = wf.add(LLMNode(provider="ollama", model="llama3.2"))
wf.connect(gatilho, dados).connect(dados, resumo)
```

### 2.2 Node — uma classe Python
Classe base abstrata. Cada Node declara **contrato** e implementa **execução**:

| Atributo | Papel |
|---|---|
| `metadata` | id, nome, versão, categoria, documentação, ícone |
| `inputs` / `outputs` | portas tipadas (schemas **Pydantic v2**) |
| `config_schema` | parâmetros do node (Pydantic) |
| `validate()` | validação estática antes da execução |
| `async def execute(ctx, inputs) -> outputs` | a lógica |

Nodes são unidades pequenas e testáveis; I/O é contrato (Pydantic), execução é assíncrona.
Carregados **dinamicamente** pelo sistema de plugins (§5).

### 2.3 Trigger — uma classe Python
Inicia execuções. Tipos de primeira classe: **Webhook** (FastAPI), **Schedule**
(APScheduler/cron), **Event** (ponte com o **EventBus** do kernel — `usuario.acordou`,
`agendamento.venceu`…), **FileWatch** (watchdog), **Polling**, **Manual**.

### 2.4 Connection e ExecutionContext
`Connection` = aresta (porta de saída → porta de entrada), com mapeamento/transformação
opcional. `ExecutionContext` carrega estado da execução, credenciais resolvidas (do cofre),
logger, tracer e hooks — injetado em cada `execute`.

## 3. A Engine (executor) — 100% Python

A Engine opera o grafo com:

- **Execução assíncrona** (`asyncio`) + **paralelismo** por análise topológica (nodes sem
  dependência entre si rodam concorrentes).
- **Filas / distribuição** atrás de um contrato (`Executor`): MVP **in-process**; produção
  com **broker** (arq/Dramatiq + Redis) sem mudar os chamadores.
- **Confiabilidade:** retries com backoff, timeout por node, **checkpoints** (estado
  persistido após cada node → execuções **resumíveis**), **compensação** estilo *saga*
  (rollback real é impossível para efeitos externos; nodes declaram ação compensatória —
  ver Risco R3).
- **Persistência de estado** (SQLAlchemy + Alembic), **logs estruturados** (structlog),
  **tracing** (OpenTelemetry), **métricas**, **eventos/hooks**, **observabilidade**.
- **Máquina de estados** da execução: `pending → running → (por node) → completed | failed |
  cancelled`, sempre checkpointada.

Bibliotecas síncronas (boto3, Selenium) são isoladas com `asyncio.to_thread` para não
bloquear o event loop.

## 4. Camadas (Clean Architecture / DDD)

```
Domínio        Workflow · Node · Trigger · Connection · ExecutionState
               (Python puro, sem I/O — SOLID, testável isoladamente)
Aplicação      casos de uso: construir · validar · executar · agendar
               (a orquestração da Engine)
Infraestrutura persistência (SQLAlchemy) · executor/broker (arq) ·
               loader de plugins (importlib) · integrações (SDKs) ·
               cofre (Fernet) · API (FastAPI) · CLI (Typer)
Interfaces     REST API · CLI · adaptador do editor visual
```

O domínio não conhece infraestrutura; adaptadores são plugáveis — protege o núcleo de
mudanças tecnológicas (mesma filosofia hexagonal do kernel).

## 5. Sistema de plugins

Todo plugin é um **pacote Python**. Descoberta automática por **entry points**
(`importlib.metadata`, grupo `teia.plugins`) + varredura de diretório (watchdog para
hot-reload em dev). Um plugin pode registrar: **Nodes, Triggers, Conectores, Ferramentas,
Integrações, Agentes de IA, comandos CLI**. Um `Registry` central coleta tudo por tipo.

**Segurança (crítico — ver Risco R2):** plugin Python = execução de código arbitrário. Por
padrão, **só plugins instalados pelo dono** (confiáveis). Plugins não confiáveis rodam em
**isolamento** (subprocesso/container) com capacidades restritas; nada é auto-instalado da
internet sem revisão. Coerente com o Sistema Imunológico Digital.

## 6. Integrações e conectores

Um `Connector` = credenciais (do **cofre Fernet**) + cliente. Prioriza-se **SDK Python
oficial/consolidado** em vez de HTTP manual: boto3, google-api-python-client, Microsoft Graph
SDK, Paramiko/Fabric, Docker SDK, GitPython, redis-py, etc. Segredos **nunca** ficam no JSON
do workflow; são resolvidos em runtime pelo cofre.

## 7. IA nativa — e a fronteira "só meu"

Suporte de primeira classe a **provedores** (OpenAI, Anthropic, Gemini, DeepSeek, Ollama,
OpenRouter, compatíveis-OpenAI) atrás de uma **interface unificada de LLM**, e a **RAG,
embeddings, vetores, ferramentas, agentes, memória, MCP, function calling, streaming**.

**A distinção que preserva a Constituição:**
- A **cognição do Kernel** (o "cérebro" do JARVIS) continua **local por padrão** (Ollama) —
  o ADR-0001..0008 não muda.
- Um **node de IA num workflow** é uma **capacidade que o dono ativa explicitamente** — se o
  dono cria um workflow que chama a OpenAI, é escolha dele (como um node "enviar e-mail"
  alcança o Gmail). Não é a mente do JARVIS vazando; é uma ferramenta do dono.
- O provedor default de qualquer node de IA é **Ollama local**; provedores de nuvem exigem
  credencial no cofre + confirmação, e são auditáveis.

Assim a plataforma "compete com Zapier/Make" em poder de IA **sem** ferir "só meu".

## 8. Interfaces (o motor nunca depende da UI)

Um mesmo workflow é: criado por **código**, carregado de **arquivo**, serializado em
**JSON/YAML**, editado no **visual**, executado por **API** e **CLI**, e **agendado**. O
frontend web é só mais um construtor que produz o mesmo objeto serializado.

## 9. Qualidade (inegociável)

PEP 8 · **tipagem completa** (mypy) · docstrings · **pytest** (unit + integração) ·
arquitetura modular · **SOLID** · **Clean Architecture** · **DDD** onde fizer sentido. Todo
node/engine entra com contrato + testes (o portão do projeto: ruff + alembic + pytest).

## 10. Escolhas tecnológicas (justificadas)

| Necessidade | Escolha | Por quê |
|---|---|---|
| API | **FastAPI** | já no projeto; async, typed, OpenAPI |
| Schemas/validação | **Pydantic v2** | contratos de I/O tipados, rápidos, serializáveis |
| Persistência | **SQLAlchemy + Alembic** | já no projeto; migrações versionadas |
| HTTP | **HTTPX** | async, sucessor do requests |
| Agendamento | **APScheduler** (ou o Scheduler do kernel) | cron/intervalo maduro |
| Fila distribuída | **arq** (Redis, asyncio) — alt. Dramatiq | async-nativo e leve; Celery é pesado/sync |
| Plugins | **importlib.metadata entry points** | padrão da stdlib, sem mágica |
| CLI | **Typer** | sobre Click, typed |
| Watch/hot-reload | **watchdog** | triggers de arquivo + dev |
| Observabilidade | **OpenTelemetry** + **structlog** | tracing + logs estruturados |
| Credenciais | **cofre Fernet do kernel** | reuso; "só meu" |
| Automação de browser/desktop | **Playwright / Selenium / PyAutoGUI** | conforme o node |

Regra: **biblioteca madura antes de implementação própria** (evita NIH).

## 11. Riscos técnicos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| **R1** | **Ambição/escopo** (competir com n8n/Zapier é enorme) | fatias verticais finas; MVP in-process; cada fase é um PR entregável |
| **R2** | **Segurança de plugins** (código arbitrário → exfiltração) | só plugins do dono por padrão; isolamento (subprocesso/container) p/ não confiáveis; sem auto-install |
| **R3** | **"Rollback" é ilusório** para efeitos externos (e-mail enviado) | ser honesto: é **compensação** (saga), best-effort; nodes declaram ação compensatória |
| **R4** | **Cloud IA × "só meu"** | node de IA = capacidade explícita do dono; default Ollama local; nuvem exige cofre + confirmação (§7) |
| **R5** | **Libs síncronas bloqueiam o event loop** | `asyncio.to_thread` / thread pool para SDKs sync |
| **R6** | **Durabilidade/exactly-once** em execução distribuída | começar in-process; broker atrás de contrato; idempotência por node (chave de execução) |
| **R7** | **Versionamento** de workflows/nodes e migração de execuções vivas | versão em metadata; execuções fixam a versão que iniciaram |
| **R8** | **Runaway/recursos** (loop infinito, consumo) | timeout por node, quotas, limite de profundidade, backpressure |
| **R9** | **Reinventar a roda** | princípio "lib madura primeiro"; conectores usam SDK oficial |

## 12. Plano incremental (cada fase = uma branch + PR, CI verde)

- **Fase 0 — Arquitetura + ADR** *(esta entrega)*: docs e contratos. Sem código.
- **Fase 1 — Núcleo de domínio** ✅ *entregue*: `Workflow`/`Node`/`Trigger`/`Connection`
  (Pydantic), serialização JSON/YAML, `Registry` em memória, algoritmos de grafo (ordem
  topológica, ciclo) e validação estrutural + por catálogo. Testes. Sem execução.
  Código em `backend-core/app/automation/teia/`.
- **Fase 2 — Engine in-process** ✅ *entregue*: executor topológico assíncrono (`Engine`),
  `RunContext` concreto (satisfaz o protocolo `ExecutionContext`), `ExecutionResult`/
  `NodeResult` estruturados, política *fail-fast* e semântica de *skip* de ramo (if/branch
  real); nodes embutidos `noop`/`set`/`transform`/`if`/`http_request` (`builtin_registry()`);
  CLI Typer (`run`/`validate`/`nodes`) para rodar um arquivo de workflow. Node HTTP testável
  offline via transporte httpx injetado. Testes. Código em `engine/`, `nodes/`, `cli.py`.
- **Fase 3 — Persistência + durabilidade**: estado em SQLAlchemy, checkpoints/resume,
  retries/timeout, logs estruturados.
- **Fase 4 — Plugins**: descoberta por entry points, formato de pacote, carga dinâmica,
  plugin de exemplo.
- **Fase 5 — Triggers**: webhook (FastAPI), schedule, **event (ponte EventBus)**, file-watch.
- **Fase 6 — Conectores + credenciais**: cofre, abstração de conector, 2-3 integrações reais
  via SDK.
- **Fase 7 — Execução distribuída**: broker (arq) atrás do contrato `Executor`,
  paralelismo/filas em escala.
- **Fase 8 — IA nativa**: interface de LLM multi-provedor (default Ollama), RAG/embeddings/
  vetores, node de agente, MCP, streaming, function calling — sob "só meu" (§7).
- **Fase 9 — Observabilidade**: OpenTelemetry, métricas, hooks/eventos.
- **Fase 10 — API do editor visual**: contrato de serialização + API para o frontend (o
  frontend web é projeto à parte).

## 13. O que muda no projeto (migração do n8n)

1. A Teia nasce como novo subsistema (`backend-core/app/automation/teia/` ou pacote próprio),
   sem tocar no kernel cognitivo.
2. O `N8nClient` atual vira **um conector legado** (não é removido) — workflows podem ser
   migrados incrementalmente.
3. A **Automation API** do North Star passa a apontar para a Teia como implementação nativa.
4. Nenhuma mudança em `main` sem PR aprovado; cada fase entra revisada e com CI verde.
