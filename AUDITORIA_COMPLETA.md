# 🔍 Auditoria Completa — Sexta-Feira OS

> Auditoria técnica profunda conduzida como preparação para elevar o projeto a nível de produto mundial.
> Data: 2026-07-16 · Escopo: 100% do repositório (código, docs, deps, infra, arquitetura).

---

## Sumário Executivo (leia isto primeiro)

**Sexta-Feira OS é hoje um _scaffold_ ambicioso e bem documentado, porém NÃO funcional de ponta a ponta.** A visão (um assistente pessoal "JARVIS" com voz, memória e automação em Android + backend + runtime cognitivo em Rust) é grande e coerente no papel, mas a implementação está em estágio de _protótipo fragmentado_:

- O app Android **não autentica** (a tela de login tem `// TODO: Implement authentication` e apenas navega para o Dashboard) e aponta para `http://localhost:8000` — endereço que **nunca** alcança o backend a partir de um device/emulador.
- O backend tem **três stacks de IA paralelas e concorrentes** (`app/jarvis/`, `app/ai/`, `app/infrastructure/ai/`) e **dois roteadores de tools com o mesmo prefixo**. Há código legado morto (`jarvis_old.py`, `routers/tools.py`).
- A "memória persistente" — diferencial nº1 do produto — **não persiste**: usa `InMemoryStore` (some ao reiniciar) e cai em _mock embeddings_ se o modelo não carregar. O orquestrador injeta `memory_service=None`, então a memória **nunca é injetada** no fluxo principal.
- O runtime cognitivo em Rust (`src/`, ~5.200 linhas, bem testado) está **órfão**: não há FFI/JNI/bindings; não é chamado pelo Android nem pelo backend. É um sub-projeto isolado.
- **~373 MB de artefatos de build commitados** (`target/` 365 MB + `.venv_new` 8,2 MB). **Zero testes** de backend/Android (só o Rust tem testes). `.env.example` referenciado no README **não existe** no repo (é ignorado pelo `.gitignore`).
- **9.412 linhas de documentação** (25 arquivos `.md`, muitos proclamando "PHASE X COMPLETE" / "TESTING COMPLETE") para **~15 mil linhas de código** que na prática não roda fim a fim. Existe um **grande descompasso documentação × realidade**.

**Veredito:** excelente material de _visão e estrutura_; imaturo como _software_. Com foco e cortes, um MVP real (login → chat com IA → memória persistida) é alcançável em **3–5 semanas**. Nota geral média ponderada: **≈ 4,0 / 10** (detalhamento na Etapa 15).

---

## Etapa 1 — Entendimento do Projeto

**Objetivo declarado:** assistente de IA pessoal "elite", inspirado em JARVIS/FRIDAY, _voice-first_, com memória persistente, automação e orquestração multi-IA, para um único dono, com privacidade. Futuro: óculos inteligentes / wearables.

**O que pretende ser:** app Android nativo (Kotlin/Compose) + backend FastAPI + orquestração multi-provedor (OpenAI/Claude/Gemini/Ollama) + memória semântica + engine de automação + runtime cognitivo de baixa latência em Rust.

**Estágio atual real:** _pré-MVP / scaffold_. Fases 1–4 declaradas "completas" na documentação, mas a integração ponta a ponta não existe.

| Funcionalidade | Estado real | Evidência |
|---|---|---|
| Autenticação backend (JWT, register/login) | **Funcional** (isolado) | `routers/auth.py`, `auth/jwt.py` (Argon2 ✔) |
| Autenticação no app Android | **Stub** | `LoginScreen.kt:81` `// TODO: Implement authentication` |
| Chat Android ↔ backend | **Quebrado** | `baseUrl("http://localhost:8000/")`, sem token |
| Chat backend ↔ Gemini | **Parcial/funcional** | `routers/jarvis.py` + `infrastructure/ai` (REST) |
| Memória persistente | **Fake** (in-memory + mock embeddings) | `di.py:76` `InMemoryConversationRepository`, `semantic.py:55` |
| Injeção de memória no prompt | **Não ligada** | `AIOrchestrator.__init__` cria `ContextInjector()` sem memory_service |
| Voz (STT/TTS) | **Endpoints existem, não validados** | `routers/voice.py` (bug `container.ai_orchestrator`) |
| Engine de automação | **Placeholder** | `routers/tools.py:138` `# TODO: Implement automation task creation` |
| Tools (registry/executor) | **Estrutura pronta, params bugados, não plugados na IA** | `infrastructure/ai/tools.py:295` args trocados |
| Runtime cognitivo Rust | **Implementado e testado, porém órfão** | `src/`, sem FFI |
| WebSocket streaming | **Parcial** | `chat_v2.py`, `infrastructure/events/websocket.py` |

**Abandonado/legado:** `jarvis_old.py` (não importado), `routers/tools.py` (mesmo prefixo do `tool_router.py` — só um é registrado), `app/ai/orchestrator.py` (singleton concorrente usado só por `chat.py`/`jarvis_old.py`), pastas DDD vazias (`domain/entities`, `domain/value_objects`, etc. com `__init__.py` de 0 bytes).

**Falta implementar:** persistência real de conversas/memória, autenticação mobile, config de rede, streaming no app, automação, testes, CI, segredos/segurança de produção, e a ponte Rust↔app (se o Rust for mantido).

---

## Etapa 2 — Mapeamento da Estrutura

```
sexta-feira-os/
├── backend-core/                 # Backend FastAPI (Python) — ~8.600 LoC
│   ├── app/
│   │   ├── main.py               # Entrypoint, lifespan, CORS, routers
│   │   ├── core/                 # config, di (ServiceContainer), security, exceptions, events, logging
│   │   ├── api/
│   │   │   ├── routers/          # auth, chat(v1), chat_v2, jarvis, jarvis_old(MORTO), memory, tools(MORTO), voice, health
│   │   │   └── tool_router.py    # /api/v2/tools (DUPLICA routers/tools.py)
│   │   ├── ai/orchestrator.py    # Orquestrador singleton (CONCORRENTE — legado)
│   │   ├── infrastructure/ai/    # providers.py, orchestrator.py, tools.py  ← stack "oficial"
│   │   ├── infrastructure/memory/semantic.py   # embeddings + InMemoryStore (NÃO persiste)
│   │   ├── infrastructure/voice/audio.py       # AudioPipeline (STT/TTS)
│   │   ├── infrastructure/events/websocket.py  # WS manager
│   │   ├── infrastructure/repositories/conversation.py  # SQL repo (NÃO usado em runtime)
│   │   ├── jarvis/               # core.py + gemini.py  ← 3ª stack de IA (SDK google.generativeai)
│   │   ├── application/use_cases/conversation.py  # ConversationPipeline
│   │   ├── application/dtos/, domain/*           # Clean/DDD scaffolding (maioria VAZIO)
│   │   ├── services/             # tool_execution_service, memory_service, conversation_tool_pipeline
│   │   ├── tools/                # registry, executor, resolver  ← 2º sistema de tools
│   │   ├── android/              # intent_builder, dispatcher, intent_service, models
│   │   ├── models/models.py      # ORM: User, ChatMessage, MemoryEntry, AutomationTask
│   │   ├── schemas/              # Pydantic
│   │   ├── auth/jwt.py           # hash Argon2, create/decode token, get_current_user
│   │   └── db/database.py        # engine/SessionLocal/Base
│   ├── requirements*.txt (x4)    # base/ai/enterprise + requirements.txt
│   └── Dockerfile
├── src/                          # Runtime cognitivo em RUST — ~5.200 LoC (ÓRFÃO)
│   ├── perception/               # voice_gate, audio_ringbuffer, screen_delta, interrupt_bus, funnel, snapshot
│   ├── cognition/                # cognitive_loop, scheduler, intent_parser, stream_decoder, tool_registry, reasoning_context
│   ├── integration/              # android_runtime, flutter_bridge, cognitive_bridge, event_mesh, secure_intent, tool_executor, observability
│   └── presentation/             # runtime, state, events
├── mobile-android/               # App Android Kotlin/Compose — ~1.230 LoC
│   └── app/src/main/kotlin/com/sextafeira/os/
│       ├── MainActivity.kt, ui/{screens,navigation,theme}, viewmodel/, data/api/, domain/model/
├── shared/constants.py           # constantes compartilhadas
├── scripts/                      # setup/start/stop/status/test (Python + shell)
├── docs/                         # architecture, api, setup, vision, README
├── examples/perception_integration.rs
├── target/  .venv_new/           # ARTEFATOS COMMITADOS (~373 MB) — devem sair do git
├── docker-compose.yml, Cargo.toml/lock, LICENSE
└── *.md (25 arquivos, 9.412 linhas)  # ARCHITECTURE-V2, PHASE3/4_COMPLETION, IMPLEMENTATION_COMPLETE, etc.
```

**Comunicação entre módulos (fluxo pretendido):**
`Android (Compose/ViewModel/Retrofit)` → `HTTP /api/v1/jarvis/chat` → `jarvis.py` → `AIOrchestrator` → `Provider (Gemini REST)` → resposta. Memória: `MemoryService(db)` (jarvis) **ou** `RetrievalPipeline/InMemoryStore` (DI) — **inconsistente**. WebSocket v2 em paralelo. O Rust **não participa** de nenhum fluxo real.

**A arquitetura faz sentido?** A _intenção_ (camadas Clean/Hexagonal, Repository, Factory, Orchestrator, DI) é sólida e apropriada. A _execução_ está fragmentada: múltiplas implementações concorrentes do mesmo conceito, camadas DDD vazias, e três "cérebros" de IA que não convergem. Falta uma decisão arquitetural única e a remoção do que não é o caminho escolhido.

---

## Etapa 3 — Arquitetura

**Padrões presentes (bem aplicados):**
- **Factory** — `ProviderFactory.create_provider` (limpo, correto).
- **Strategy/Adapter** — `BaseAIProvider` + implementações por provedor (boa abstração).
- **Registry** — `tools/registry.py`, `cognition/tool_registry.rs` (bem feitos).
- **Repository** — interface `MemoryStore`, `SQLConversationRepository` (existe, mas não é usado em runtime).
- **DI/Service Locator** — `ServiceContainer` + `dependency_overrides` (razoável, porém é _service locator_ global, não DI verdadeira).
- **Rust**: separação Perception → Cognition → Integration → Presentation é elegante e idiomática, com _budgets_ de latência e testes.

**Problemas de arquitetura:**
1. **Três stacks de IA concorrentes** (`app/jarvis`, `app/ai`, `app/infrastructure/ai`) — violação grave de DRY e fonte única de verdade.
2. **Camadas DDD vazias** — `domain/entities`, `domain/value_objects`, `domain/repositories`, `application/dtos` são `__init__.py` de 0 byte. "Clean Architecture" é anunciada mas não materializada; as regras de negócio moram em routers e no container.
3. **SOLID** — SRP violado (routers fazem auth+orquestração+formatação); DIP parcial (orquestrador depende de provedores concretos via factory, ok, mas `ContextInjector` recebe `None` e a dependência de memória é ignorada).
4. **Acoplamento a estado global mutável** — `AgentRegistry._agents`, `ToolRegistry._tools` (class-level em `jarvis/core.py`), `GeminiOrchestratorV2.conversation_history` (instância singleton) → **estado compartilhado entre todos os usuários** (bug de concorrência/privacidade).
5. **Runtime Rust desconectado** — decisão arquitetural não resolvida: é o "core" ou um experimento? Hoje é peso morto no produto.
6. **Versionamento de API inconsistente** — `v1` (auth/chat/jarvis/memory) e `v2` (chat_v2/voice/tools) coexistem sem estratégia; `config.api_prefix="/api/v2"` não é usado.

**Bem feito:** abstração de provedores; estrutura de pastas legível; separação mobile/backend; Rust idiomático e testado.

**Precisa reestruturar:** escolher **uma** stack de IA; materializar (ou remover) as camadas DDD; unificar tools; decidir o destino do Rust; unificar versionamento; eliminar estado global mutável por-request/por-usuário.

**O que eu mudaria:** colapsar para **um** `ai/` (providers + orchestrator + tools), com memória injetada de fato; repositórios SQL reais como padrão; um único `/api/v1`; Rust extraído para outro repositório até haver FFI real.

---

## Etapa 4 — Código (smells, duplicação, morto)

**Código morto/legado (remover):**
- `app/api/routers/jarvis_old.py` (230 linhas) — não importado.
- `app/api/routers/tools.py` — mesmo prefixo `/api/v2/tools` do `tool_router.py`; só `tool_router` é registrado no `main.py` → arquivo órfão (com TODOs de automação).
- `app/ai/orchestrator.py` (183 linhas) — usado apenas por `chat.py` (v1) e pelo morto `jarvis_old.py`.
- Pastas DDD vazias (13 `__init__.py` de 0 byte).
- `target/` (365 MB) e `.venv_new/` (8,2 MB) commitados.

**Duplicação:**
- **Duas classes `GeminiProvider`** (`jarvis/gemini.py` via SDK vs `infrastructure/ai/providers.py` via REST) com comportamento divergente.
- **Dois sistemas de tools** (`app/tools/*` e `app/infrastructure/ai/tools.py`) + **dois registries** (`ToolRegistry` em `tools/registry.py` e em `jarvis/core.py`).
- Lógica de `get_current_user` reimplementada em `auth/jwt.py`, `core/security.py` e localmente em `jarvis.py`.
- Blocos `if not hasattr(container, 'audio_pipeline')` repetidos 4× em `voice.py`.

**Bug real de código (não só smell):** em `infrastructure/ai/tools.py`, as `ToolParameter` dos tools padrão passam argumentos **posicionais trocados**:
`ToolParameter("query", "Search query", "string")` — a assinatura é `(name, type, description, ...)`, logo `type="Search query"` e `description="string"`. **Todos os tools padrão têm `type`/`description` invertidos**, gerando schema OpenAI inválido.

**Outros smells:**
- `voice.py:30` `audio_pipeline = container.ai_orchestrator  # TODO` — variável atribuída ao objeto errado e nunca usada.
- `hasattr(container, 'audio_pipeline')` é sempre `True` (inicializado como `None` no `__init__`) → branch de fallback é código morto.
- Homóglifos cirílicos no código: `config.py` `app_name = "Sexта-Feira OS"` (о "т"/"а" são cirílicos) e docstrings — quebra buscas e i18n.
- `datetime.utcnow()` (deprecado no 3.12) usado nos models/serviços; `auth/jwt.py` já usa `timezone.utc` (inconsistência).
- Imports pesados dentro de funções (`voice.py`), dificultando análise estática.
- Comentários "CORREÇÃO/FIX" em `main.py` indicam _fixes_ acumulados sem limpeza.

**Coesão/acoplamento:** baixa coesão nos routers (misturam responsabilidades); alto acoplamento a singletons globais.

---

## Etapa 5 — Bugs (com causa raiz, impacto e solução)

| # | Severidade | Bug | Causa raiz | Impacto | Solução |
|---|---|---|---|---|---|
| 1 | 🔴 Crítica | App nunca autentica | `LoginScreen.kt:81` só navega, sem chamar `login()` nem setar token | Produto inutilizável fim a fim | Chamar `apiService.login`, persistir token (DataStore), injetar no `ChatViewModel` |
| 2 | 🔴 Crítica | App não alcança backend | `baseUrl("http://localhost:8000/")` | Toda request falha no device/emulador | `10.0.2.2` p/ emulador, base URL por _build config_/env; HTTPS |
| 3 | 🔴 Crítica | Memória não persiste | `di.py` usa `InMemoryConversationRepository`; `InMemoryStore` volátil | "Persistent memory" (diferencial) é falso; perda ao reiniciar | Trocar por `SQLConversationRepository` + vector store real (pgvector/Chroma) |
| 4 | 🔴 Crítica | Memória nunca injetada no prompt | `AIOrchestrator.__init__` cria `ContextInjector()` sem `memory_service`; `jarvis.py` chama `orchestrator.generate` direto | Respostas sem contexto | Passar `retrieval_pipeline` ao `ContextInjector`; rotear via `ConversationPipeline` |
| 5 | 🟠 Alta | `conversation_id` sempre `null` | `jarvis.py` ecoa `request.conversation_id`; app só seta se ≠ null | Nunca há continuidade de conversa | Gerar/retornar id no backend e persistir |
| 6 | 🟠 Alta | Tools padrão com schema inválido | Args posicionais trocados em `ToolParameter` | Function-calling quebrado | Usar kwargs: `ToolParameter(name=..., type=..., description=...)` |
| 7 | 🟠 Alta | Estado global entre usuários | `GeminiOrchestratorV2.conversation_history`, `AgentRegistry._agents`, `ToolRegistry._tools` class-level | Vazamento de contexto entre usuários (privacidade) | Estado por-usuário/por-request; remover singletons mutáveis |
| 8 | 🟠 Alta | Streaming com fallback re-emite | `AIOrchestrator.stream_generate` faz fallback após já ter feito `yield` | Saída duplicada/corrompida em falha parcial | Só permitir fallback antes do 1º chunk; buffer inicial |
| 9 | 🟡 Média | `torch>=2.12.0` inexistente | Versão errada em `requirements-ai.txt` | `pip install` falha | Fixar `torch` versão real (ex.: 2.3.x CPU) |
| 10 | 🟡 Média | Pacote Gemini errado | Código importa `google.generativeai`, mas requirements traz `google-genai==0.1.0` | `ImportError` → provider SDK vira `None` | Usar `google-generativeai` **ou** migrar código p/ `google-genai` |
| 11 | 🟡 Média | `.env.example` ausente | `.gitignore` `.env*` ignora o exemplo; README manda copiá-lo | Onboarding quebrado | Renomear p/ `.env.template` e versionar; ajustar `.gitignore` |
| 12 | 🟡 Média | CORS x credenciais | `allow_origins` lista fixa + `allow_credentials=True` + métodos `*`; sem origins de prod | Falha em prod / risco | Origins por env; sem `*` com credenciais |
| 13 | 🟡 Média | `Base.metadata.create_all` no boot | `main.py` cria schema no startup, sem migrações reais (Alembic instalado, não usado) | Divergência de schema, sem versionamento | Alembic migrations no deploy |

---

## Etapa 6 — Performance

- **Modelo de embeddings carregado no boot** (`EmbeddingService.initialize`) — `SentenceTransformer` + `torch` no processo web bloqueiam startup e consomem RAM (~300–500 MB). Deveria ser _lazy_ e/ou em serviço separado.
- **Busca semântica O(n) linear** em `InMemoryStore.search` (cosine em loop Python/NumPy sobre todas as memórias) — não escala além de milhares de itens. Usar índice ANN (FAISS/pgvector/HNSW).
- **`httpx.AsyncClient` recriado a cada request** (novo cliente por chamada em todos os providers) — sem _connection pooling_ nem _keep-alive_; adiciona latência de handshake TLS. Reusar um cliente compartilhado.
- **Sem cache** — Redis está no compose, mas nenhum código o usa. Respostas de IA, embeddings e health não são cacheados.
- **Sem paginação** em listagens (memórias, conversas) e sem limites server-side robustos.
- **Health check faz round-trip ao provedor externo** a cada chamada (`default_provider.health_check()`), podendo custar latência/quotas.
- **Rust**: o único componente com foco explícito em performance (budgets sub-50 ms, `opt-level=3`, `lto`), mas irrelevante enquanto órfão.
- **Android**: `Retrofit` sem timeouts, sem `OkHttp` interceptors, sem streaming; recomposição não avaliada.

**Gargalos-chave:** startup do backend (ML no boot), busca de memória linear, ausência de pooling HTTP e de cache.

---

## Etapa 7 — Segurança (auditoria)

**Positivos:** hashing de senha **Argon2** (correto e moderno); JWT com `exp`/`iat`; Pydantic para validação de entrada; sem segredos reais commitados (varredura não encontrou chaves).

**Riscos:**
1. 🔴 **JWT secret default fraco** — `"dev-secret-key-change-in-production"` e no compose `"dev-secret-key-change-in-prod"`; sem _fail-fast_ se não sobrescrito em produção. Qualquer um forja tokens. **Solução:** exigir `JWT_SECRET_KEY` forte, abortar boot em prod se default.
2. 🔴 **Registro aberto** num produto "single-owner" — `/auth/register` cria qualquer usuário. **Solução:** desabilitar/registrar via convite; _rate limit_.
3. 🟠 **Sem autorização/escopos** — só "autenticado vs não". Sem roles, sem verificação de _ownership_ além de `user_id==` manual. Risco de IDOR nos endpoints de memória/tools.
4. 🟠 **Rate limiting inexistente** — `rate_limit_enabled` é só flag de config; nenhum middleware implementa. Exposto a abuso/força-bruta no login e custo de IA.
5. 🟠 **`calculate` tool avalia expressão matemática** — se implementado via `eval`, é **RCE**. Verificar/forçar parser seguro (ast/`simpleeval`).
6. 🟠 **Cleartext HTTP no app** (`http://`), tokens em memória, sem _certificate pinning_ — interceptação/MITM.
7. 🟡 **CORS** com `allowed_origins="*"` (config) e credenciais — potencial CSRF/roubo.
8. 🟡 **Segredos via API key na URL** (Gemini `params={"key": ...}`) — vaza em logs/proxies. Preferir header quando possível.
9. 🟡 **Erros vazam `str(e)` ao cliente** (`detail=f"...{e}"`) em vários routers — _information disclosure_.
10. 🟡 **LGPD** — dados pessoais (memórias, conversas) sem criptografia em repouso, sem política de retenção efetiva (`memory_retention_days` não aplicado), sem export/delete (direito do titular), sem consentimento/auditoria. Contradiz o pilar "privacy-by-design" da visão.

---

## Etapa 8 — Inteligência Artificial

**Como funciona hoje:** request → `AIOrchestrator` tenta `default_provider` e cai para _fallbacks_ (cadeia). Providers falam REST (OpenAI-compat para Gemini). Há um `PromptManager` com 4 prompts de sistema e um `ToolCallingEngine` **não conectado** aos tools reais. Memória **não** é injetada (bug #4). Existe ainda a stack `jarvis/` (SDK) e `app/ai` (singleton), não usadas pelo caminho principal → **três cérebros, nenhum completo**.

**Como deveria funcionar:**
- **Uma** camada de IA canônica: `providers/` (adapters) → `orchestrator` (roteamento por _capability_/custo/latência, não só fallback) → `context` (memória + histórico + perfil) → `tools` (function-calling real, com _tool loop_) → `guardrails`.
- **Memória em camadas**: curto prazo (janela da conversa), episódica (interações), semântica (fatos/preferências via vetores) e sumarização (compressão de conversas antigas — o `ConversationCompressor` existe, mas não é acionado).
- **Agentes especializados** (o scaffold `Agent`/`AgentCapability` já sugere isto): _Chat_, _Planner_, _Analyst_, _Automation_ — cada um com prompt/tools próprios, orquestrados por um _router agent_.

**O que falta:** _tool-calling loop_ (detectar chamada → executar → devolver resultado → continuar), streaming unificado, contagem/orçamento de tokens (hoje `tokens_used=0` no Gemini), _retries_/_timeouts_/_circuit breaker_ por provider, _caching_ semântico, avaliação de qualidade.

**Escalar / reduzir consumo / aumentar precisão:** cache de respostas e embeddings; roteamento _cost-aware_ (modelo barato p/ tarefas simples); _prompt caching_; truncamento/compressão de contexto; ANN para recuperar só o relevante; _few-shot_ dinâmico a partir da memória; métricas de acerto.

**Memória/contexto/aprendizado:** persistir tudo (SQL + vetorial), extrair fatos automaticamente (o `memory_service.py:117` tem esse TODO), pontuar importância/decay, e _feedback loop_ (👍/👎) para reforçar preferências.

---

## Etapa 9 — Experiência do Usuário

- **Fluxo quebrado**: Splash → Login (não autentica) → Dashboard → Chat (não conecta). O usuário nunca completa a jornada.
- **UI**: Compose + Material 3 com tema/tipografia definidos — base visual decente e moderna (`ChatAssistantScreen` 244 linhas é a tela mais rica).
- **Sem feedback de erro real** (token ausente mostra "Not authenticated", mas nunca há token); sem _loading states_ ligados ao backend real; sem tela de configuração de servidor/API key.
- **Voice-first** é o pilar do produto, mas **não há captura de voz no app** (só endpoints no backend). O diferencial nº1 está ausente na UI.
- **Sem onboarding**, sem persistência de sessão, sem modo offline.

**Sugestões:** implementar login real + _session persistence_; tela de settings (URL do backend, chaves, voz); indicador de status do backend/IA; captura de voz (SpeechRecognizer/gravação + envio ao `/voice`); streaming token-a-token no chat; estados de erro/vazio/carregando consistentes.

---

## Etapa 10 — Documentação

- **Volume enorme**: 25 `.md` / 9.412 linhas (README, PROJECT_CONTEXT, vision, ROADMAP, ARCHITECTURE-V2, SYSTEM_ARCHITECTURE, PHASE3/4_COMPLETION, IMPLEMENTATION_COMPLETE, TESTING_COMPLETE, DELIVERY_SUMMARY, EXECUTIVE_SUMMARY, FILES_CREATED, REFACTORING_*...).
- **Qualidade de visão**: alta. A narrativa de produto é clara e inspiradora.
- **Problema central**: **documentação descreve um sistema que não existe**. Arquivos "COMPLETE"/"TESTING_COMPLETE" contradizem a ausência de testes e a falta de integração. Isso é _dívida de credibilidade_: um novo dev é induzido ao erro.
- **Lacunas operacionais**: `.env.example` ausente; README manda `python -m uvicorn app.main:app` mas o boot depende de `initialize_services` (que exige chave de IA válida, senão `raise` → app não sobe); sem diagrama real de sequência atualizado; sem doc de qual stack de IA é a "oficial".
- Um dev **não** consegue subir o projeto rapidamente hoje.

**Recomendação:** consolidar em ~5 docs vivos (README, ARCHITECTURE, SETUP, API, ROADMAP), remover os "COMPLETE"/status snapshots, e alinhar 100% com o código. Documentação deve seguir o código, não precedê-lo em fantasia.

---

## Etapa 11 — Testes

- **Backend/Android: 0 testes.** Só existe `scripts/test-jarvis.py` (script manual) e `TESTING_COMPLETE.md` (documento que **afirma** cobertura completa — falso).
- **Rust: bom** — 94 funções de teste em 21 arquivos (`#[tokio::test]`/`#[test]`), o único componente testado. Ironia: é o órfão.
- `pytest`/`pytest-asyncio` estão nas deps mas não há suíte, `conftest.py`, nem CI.
- **Sem CI** (nenhum `.github/workflows`), sem lint gate, sem cobertura.

**Falta:** unit (auth/jwt, providers com mocks httpx, memory store, tools), integração (endpoints via `TestClient`), contrato (schemas Android ↔ backend), E2E (login→chat→memória), e do lado Android (ViewModel/Compose/UI tests). Meta inicial realista: **60–70%** no core do backend.

---

## Etapa 12 — Dependências

- **Duplicação/confusão**: 4 arquivos de requirements (`requirements.txt`, `-base`, `-ai`, `-enterprise`) sem hierarquia clara documentada; risco de divergência.
- **Versão inexistente**: `torch>=2.12.0` (não existe) → instalação falha.
- **Pacote errado**: `google-genai==0.1.0` vs uso de `google.generativeai` (pacote `google-generativeai`).
- **Deps instaladas mas não usadas**: `openai`, `anthropic` (providers usam httpx cru), `scikit-learn`, `aiohttp`+`requests` (já há httpx), `passlib[bcrypt]` (usa-se Argon2), `alembic` (sem migrações).
- **Pesadas para um web dyno**: `torch` + `sentence-transformers` no mesmo processo do FastAPI.
- **Pinning inconsistente** (mistura `==` e `>=`). Sem _lockfile_ (pip-tools/poetry/uv) → builds não reprodutíveis.
- **Android**: sem DI (Hilt), sem persistência (DataStore/Room), Retrofit+Gson (considerar Moshi/kotlinx).
- **Rust**: só `tokio` — enxuto e bom.

**Ações:** um `pyproject.toml` com `uv`/poetry + lock; remover não usados; corrigir torch/gemini; separar ML em _extra_ opcional ou serviço.

---

## Etapa 13 — Banco de Dados

- **Modelagem** (`models.py`): `User`, `ChatMessage`, `MemoryEntry`, `AutomationTask` — razoável para MVP, com índices em FKs e `created_at`.
- **Problemas**:
  - **PKs `String` sem default no servidor** — id gerado na app (`uuid4`); ok, mas sem `server_default`.
  - **`MemoryEntry` sem coluna de embedding/vetor** — a "memória semântica" real não tem onde persistir vetores; o `InMemoryStore` nem toca o banco. Modelo e serviço de memória estão **desconectados**.
  - **Sem migrações** — `alembic` presente, mas usa-se `create_all` no boot. Qualquer alteração de schema quebra em produção.
  - **Sem constraints** além de `unique(email)`; faltam `nullable=False`, `ondelete` nas FKs, e índice composto (`user_id, created_at`) para histórico.
  - **Integridade**: `ChatMessage`/`MemoryEntry` não têm cascade; deletar usuário deixa órfãos.
  - **Escalabilidade**: SQLite default (dev) e PostgreSQL (prod) — sem pgvector para busca vetorial; busca semântica não usa o DB.
  - **Normalização**: `AutomationTask.action` como `Text` livre (deveria ser estruturado/JSON validado).

**Ações:** adicionar `pgvector` + coluna `embedding` em `MemoryEntry`; Alembic desde já; constraints e índices compostos; separar `Conversation`/`Message` (hoje só `ChatMessage` flat).

---

## Etapa 14 — Roadmap

**🔴 Correções críticas (Semana 1–2) — "fazer funcionar":**
1. Login real no Android + persistência de token + base URL configurável (`10.0.2.2`/env).
2. Persistir conversas/memória: trocar stubs por `SQLConversationRepository` + vector store.
3. Ligar memória ao prompt (`ContextInjector` com `retrieval_pipeline`).
4. Corrigir deps (`torch`, pacote Gemini), `.env.example`, boot que não aborta sem chave.
5. JWT secret _fail-fast_ em prod; fechar/gate no `/register`.

**🟠 Importantes (Semana 3–4):**
6. Escolher **uma** stack de IA; remover `jarvis_old.py`, `routers/tools.py`, `app/ai/orchestrator.py`, camadas DDD vazias.
7. `.gitignore` de `target/`/`.venv_new/`; purgar do histórico (git filter-repo) → repo ~ -373 MB.
8. Rate limiting (slowapi), erros sem vazar stack, CORS por env.
9. Alembic + constraints + índices.
10. Suíte de testes backend (auth, providers mockados, memória, endpoints) + CI GitHub Actions.

**🟢 Melhorias / Refatorações / Otimizações (Mês 2):**
11. Tool-calling loop real; corrigir schema dos tools.
12. Cliente httpx compartilhado + Redis cache + ANN (pgvector/FAISS).
13. Captura de voz no app + streaming no chat.
14. ML de embeddings como serviço/opcional (tirar do boot web).
15. Consolidar documentação (5 docs vivos).

**🔵 Arquitetura futura / Novas funcionalidades (Mês 3+):**
16. Engine de automação (triggers/scheduler) de verdade.
17. Agentes especializados + roteamento cost/capability-aware.
18. Decidir Rust: extrair p/ repo próprio e criar FFI (UniFFI/JNI) se for o core de baixa latência; senão, remover.
19. Observabilidade (OpenTelemetry/Prometheus — já há flags), LGPD (export/delete/cripto em repouso).

**Tecnologias recomendadas:** `uv`/poetry + lock; `pgvector`; `slowapi`; `Alembic`; `OpenTelemetry`; Android: Hilt + DataStore + Room + OkHttp; CI: GitHub Actions (lint+test+build).

---

## Etapa 15 — Score (0–10)

| Dimensão | Nota | Justificativa |
|---|---:|---|
| Arquitetura | 5.0 | Boa intenção/padrões; execução fragmentada, 3 stacks de IA, DDD vazio |
| Código | 4.0 | Legível, mas duplicado, morto, com bugs reais (params, homóglifos) |
| Organização (pastas) | 6.0 | Estrutura clara; poluída por artefatos e módulos órfãos |
| Escalabilidade | 3.5 | Busca O(n), sem cache, ML no boot, memória volátil |
| Segurança | 3.0 | Argon2 ✔; JWT default, sem rate limit/authz, register aberto, LGPD ausente |
| Performance | 4.0 | Rust focado (órfão); backend sem pooling/cache |
| Qualidade | 3.5 | Sem testes (exceto Rust), sem CI, bugs de integração |
| Documentação | 5.0 | Vasta e inspiradora, porém descolada da realidade |
| UX | 3.5 | UI Compose decente; fluxo não funciona, sem voz na UI |
| IA | 4.0 | Abstração boa; memória não ligada, sem tool-loop, 3 cérebros |
| Banco | 4.0 | Modelo ok; sem migrações, sem vetor, desconectado da memória |
| Testes | 2.5 | 0 no backend/app; bom só no Rust órfão |
| Deploy | 4.5 | Docker/compose ok; roda como root, sem migrações, secrets fracos |
| Manutenibilidade | 4.0 | Duplicação e morto elevam o custo de mudança |
| Legibilidade | 6.5 | Nomes/documentação inline claros; melhor ponto do código |
| Organização do projeto | 4.5 | Visão clara; disciplina de repo/estado real baixa |

**Média ≈ 4,2 / 10** — _protótipo promissor, longe de produção._

---

## Etapa 16 — O que eu faria (como arquiteto-chefe)

- **Manteria:** a visão/produto; a abstração de providers (`BaseAIProvider`+Factory); os registries/executor de tools; a base Compose/Material 3; o hashing Argon2; e o runtime Rust **como repositório separado** (é bom demais para jogar fora, mas não pertence a este repo ainda).
- **Removeria:** `jarvis_old.py`, `routers/tools.py`, `app/ai/orchestrator.py`, `app/jarvis/*` (ou `infrastructure/ai/*` — manter só um), camadas DDD vazias, `target/` e `.venv_new/` do git, docs "COMPLETE".
- **Reescreveria:** o fluxo de auth do Android (real), a camada de memória (persistente + vetorial + injetada), o `ConversationPipeline` como caminho único, e o schema dos tools.
- **Modularizaria:** IA em `ai/{providers,orchestrator,context,tools,agents}`; memória num serviço próprio; rede/config do Android num módulo `core`.
- **Automatizaria:** CI (lint+test+build), migrações Alembic no deploy, lockfile de deps, pre-commit.
- **Simplificaria:** um único versionamento `/api/v1`; um cliente HTTP; menos requirements; menos docs (vivas).
- **Deixaria pronto p/ o futuro:** interfaces de memória/agentes estáveis; `pgvector`; observabilidade ligada; FFI-ready para trazer o Rust quando fizer sentido.

---

## Etapa 17 — Relatório Final

**1. Resumo executivo:** ver topo. Scaffold visionário, não funcional fim a fim; MVP real a ~3–5 semanas com foco.

**2. Estado atual:** pré-MVP. Auth backend e chat backend↔Gemini funcionam isolados; app não autentica nem conecta; memória fake; Rust órfão; sem testes/CI; repo inflado.

**3. Pontos fortes:** visão de produto clara; abstração de providers; Rust idiomático e testado; UI Compose moderna; Argon2; estrutura de pastas legível.

**4. Pontos fracos:** três stacks de IA; memória não persiste nem injeta; fluxo mobile quebrado; 0 testes no core; segurança de produção ausente; docs descoladas; ~373 MB de lixo versionado.

**5. Bugs:** ver Etapa 5 (13 itens; 4 críticos).

**6. Gargalos:** ML no boot; busca de memória O(n); sem pooling HTTP; sem cache. (Etapa 6)

**7. Dívidas técnicas:** duplicação/legado; DDD vazio; sem migrações; deps quebradas; estado global mutável; versionamento misto.

**8. Riscos:** JWT fraco; register aberto; sem rate limit/authz; possível RCE em `calculate`; LGPD; MITM no app; disclosure de erros.

**9. Melhorias sugeridas:** ver Etapas 14/16.

**10. Plano de refatoração:** unificar IA → remover morto → persistência real → memória injetada → tools corrigidos → testes/CI. (Etapa 14, blocos 🔴🟠)

**11. Plano de evolução:** voz na UI → automação → agentes especializados → observabilidade/LGPD → decisão do Rust. (blocos 🟢🔵)

**12. Arquitetura ideal:** Android (Compose + Hilt + DataStore/Room + OkHttp/streaming) ↔ FastAPI (`/api/v1` único, Clean real e enxuto) → `ai/` canônico (providers/orchestrator/context/tools/agents) → Postgres+pgvector (memória em camadas) + Redis (cache) → observabilidade OTel → (futuro) core Rust via FFI. Migrações Alembic, secrets geridos, CI/CD.

**13. Lista priorizada de tarefas:** (P0) login+rede Android, persistência de memória, injeção de memória, deps/torch/gemini, `.env.example`, JWT fail-fast. (P1) unificar IA/remover morto, limpar git de artefatos, rate limit, Alembic, testes+CI. (P2) tool-loop, cache/pooling/ANN, voz na UI, docs. (P3) automação, agentes, Rust/FFI, LGPD.

**14. Estimativa de esforço** (1 dev pleno):
- P0 ≈ 8–12 dias · P1 ≈ 10–15 dias · P2 ≈ 15–20 dias · P3 ≈ 25–40 dias.
- **MVP funcional (P0+parte do P1): ~3–5 semanas.**

**15. Impacto esperado:**
- P0 → produto **passa a funcionar** fim a fim (impacto máximo).
- Limpeza/unificação → −40–60% de custo de manutenção; repo −373 MB.
- Testes+CI → regressões caem drasticamente; confiança de release.
- Cache/pooling/ANN → latência e custo de IA menores; escala real.
- Segurança/LGPD → apto a usuários reais/beta.

**16. Conclusão final:** Sexta-Feira OS tem **alma de produto e ossatura de arquitetura**, mas ainda não tem **músculo de engenharia**. O maior risco não é técnico e sim de _percepção_: a documentação afirma "completo" onde há stubs. O caminho é honesto e direto — **consolidar (um cérebro de IA), conectar (login→chat→memória real), limpar (morto/artefatos) e provar (testes/CI)**. Feito isso, a visão JARVIS deixa de ser narrativa e vira software. A fundação é boa o suficiente para justificar o investimento; a execução precisa de disciplina, cortes e foco em _um_ fluxo que funcione de verdade antes de expandir.

---

*Auditoria baseada na leitura direta do código-fonte (backend Python, app Android Kotlin, runtime Rust), dependências, infraestrutura e documentação do repositório.*
