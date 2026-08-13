# Arquitetura — Sexta-Feira (kernel local)

## Visão em uma frase

**Um cérebro privado na sua máquina; vários corpos (celular, carro, óculos, relógio)
que se conectam a ele pela sua rede privada. Nada sai do host.**

## Camadas

```
Corpos ──HTTP privado──► Kernel (FastAPI) ──► Cognition ──► LocalBrain ──► Ollama
                                                  │
                                                  └──► PersistentMemory ──► SQLite
```

### 1. Corpos (clientes)
App Android hoje; futuramente carro/óculos/relógio. Cada corpo é **pareado** pelo dono
e recebe um token de dispositivo de longa duração. Autenticação = o dono, opcionalmente
agindo através de um corpo pareado.

### 2. Kernel (`backend-core/app`)
- `main.py` — bootstrap, CORS loopback, lifespan.
- `core/config.py` — configuração local, modos de acesso (loopback/lan/tunnel), persona.
- `core/di.py` — `Kernel`: monta brain + memory + cognition; cria o dono no 1º boot.
- `auth/jwt.py` — tokens de dono e de dispositivo (Argon2, fail-fast do segredo em produção).
- `api/routers/` — `health`, `auth` (login + pareamento), `chat`, `memory`.

### 3. Cérebro (`app/brain`)
- `engine.py` — `LocalBrain`: única via de inferência. Fala com o Ollama local para
  **chat** e **embeddings**. Cliente httpx compartilhado (pooling). Sem nuvem.
- `memory.py` — `PersistentMemory`: **grafo de conhecimento**. Cada memória é um nó;
  arestas (`MemoryLink`) conectam nós via `[[wikilinks]]`, similaridade semântica
  (embeddings locais) e ligações manuais. As arestas automáticas são **nomeadas pelo
  cérebro** ("trabalha em", "gosta de"...) — não só "related". A recuperação faz *seed*
  por similaridade e **expande pelas arestas** (backlinks incluídos) — pensamento em
  rede à la Obsidian. Tudo no SQLite, sobrevive a reinícios.
- `cognition.py` — o loop: persona + memória recuperada + histórico + mensagem →
  resposta; persiste os turnos; auto-aprende um fato durável (best-effort).
- `teach.py` — transforma história + memórias em dataset de fine-tuning.

### 3b. Voz (`app/voice`)
Ouvir e falar, 100% local e **opcional** (extra `requirements-voice.txt`):
- `stt.py` — `Transcriber` (faster-whisper): áudio → texto, offline.
- `tts.py` — `Synthesizer` (Piper): texto → áudio, offline.
- `box.py` — `VoiceBox`: carrega os motores sob demanda; degrada com 503 limpo se ausentes.
Endpoints em `api/routers/voice.py`, incluindo `/voice/chat` (ouve → pensa com memória → responde falando).

### 3c. Automações (`app/automation`) — as mãos
Ponte para um **n8n self-hosted** (local). `N8nClient` lista workflows (Public API) e
os dispara por Webhook. Degrada com 503 se o n8n estiver fora. É assim que o Sexta-Feira
**age** no mundo (milhares de integrações). Endpoints em `api/routers/automation.py`.
O n8n sobe junto no `docker-compose.yml`, só em loopback.

### 3c-bis. Protocolo de Ação (`app/action`) — as mãos em cada corpo
Transporte de ações do cérebro para os dispositivos. `ActionService` persiste um comando
`{action, params}` para o corpo alvo (resolvido por sinônimo — "celular"→phone — ou nome)
e o entrega: em tempo real pelo `CommandBus` (WebSocket) se online, ou pela fila (polling)
quando reconecta. O dispositivo reporta o resultado. **Fire-and-forget** — nunca bloqueia.
O *vocabulário* de ações é do dispositivo, não do kernel (extensível sem mudar o kernel).
Endpoints em `api/routers/action.py` (`/actions/dispatch`, `/actions/stream` WS,
`/actions/pending`, `/actions/{id}/result`).

### 3c-ter. Agendador (`app/schedule`) — o senso de tempo
`Scheduler` guarda intenções futuras (lembretes e ações com hora) e as dispara quando
vencem, pelo Protocolo de Ação (um lembrete vira uma ação `notify` no celular). `run_due`
é um método puro e determinístico (fácil de testar); um loop de fundo (config
`SCHEDULER_ENABLED`) só o chama no intervalo. Suporta recorrência. Endpoints em
`api/routers/schedule.py`.

### 3c-4. Conectores de API (`app/connectors`) — executar (quase) tudo
Registro de **capacidades**: cada uma é uma chamada de API que o dono define (método,
url, query, headers, body — com templates `{param}` e `{secret:NOME}`). O cérebro
invoca **por nome** (`call_api`), nunca uma URL arbitrária → sem SSRF por prompt
injection. Segredos ficam num **cofre Fernet** (`vault.py`), criptografados em repouso,
nunca retornados pela API. Endpoints em `api/routers/connectors.py`. Escala para
milhares de APIs sem mudar o kernel. Seed inicial: `scripts/seed_connectors.py`.

### 3c-5. Sub-agentes (`app/brain/subagents.py`) — o cérebro cria auxiliares
`SubAgentRunner`: o cérebro pode `delegate(role, task)` a um sub-agente que roda no
**mesmo modelo local**, com um **toolset restrito** (`SUBAGENT_ALLOWED_TOOLS`, por padrão
só consulta/conhecimento — nada irreversível), faz sua parte e devolve um resultado
conciso. Sub-agentes **não podem delegar** (sem recursão) e são owner-scoped — não
violam o "só meu". É o mesmo laço de ferramentas, isolado e limitado.

### 3d. Tool-calling agêntico (`app/brain/tools.py`) — pensar → agir
`ToolKit` expõe ao cérebro ferramentas que ele decide usar sozinho durante a conversa
(`remember`, `recall`, `run_automation`) via tool-calling nativo do Ollama. O laço vive
em `cognition._run_with_tools`: pergunta ao cérebro → se ele pede uma ação, executa,
devolve o resultado e continua até a resposta final. Assim, do **celular por voz**, sem
terminal: "me lembra do dentista amanhã" → o cérebro chama a automação/memória certa e
confirma em linguagem natural.

## Fluxo de uma conversa

1. Corpo envia `POST /api/v1/chat {message, conversation_id?}` com o token.
2. `Cognition` carrega/cria a conversa e o histórico recente (persistido).
3. `PersistentMemory.recall` busca memórias relevantes (embeddings locais).
4. Monta `[system(persona+memória)] + histórico + mensagem` e chama o `LocalBrain`.
5. Persiste os dois turnos; opcionalmente destila um fato para a memória.
6. Retorna `{reply, conversation_id}`.

## Modelos: um cérebro, um embedder

O kernel roda **um** modelo generativo. Ele conversa, decide usar ferramentas e
enxerga — `BRAIN_MODEL` precisa reportar `tools` e `vision` em `/api/show`, e o
boot avisa se não reportar. Ao lado dele vive só o `EMBEDDING_MODEL`, que não é
um modelo de chat: transformar texto em vetor é outro ofício, e cabe em 274 MB.

Eram dois generativos, e o custo aparecia em dois lugares. O Ollama mantém os
modelos residentes por `keep_alive` e despeja um para carregar o outro, então em
12 GB de RAM cada frame de câmera derrubava o modelo de conversa e a mensagem
seguinte pagava o carregamento a frio. E como só um dos dois tinha ferramentas,
nenhum turno conseguia ver uma imagem e agir sobre ela: a visão era um serviço
consultado à parte, cuja resposta voltava como texto.

Com um modelo só, `LocalBrain.chat_with_tools(..., images=[...])` entrega os
pixels e as ferramentas na mesma chamada. `VisionEngine` continua existindo para
as perguntas fechadas sobre uma imagem (OCR, descrever cena, ler documento) e,
por padrão, aponta para o mesmo modelo — ver `settings.vision_model_resolved`.

## Como ele aprende (fine-tuning)

`export_training_data.py` → `dataset.jsonl` → `finetune_lora.py` (LoRA, offline, GPU) →
merge para GGUF → `ollama create sexta` → `BRAIN_MODEL=sexta`. O runtime não muda:
o kernel continua chamando o Ollama; só o modelo ficou mais *seu*.

## Privacidade

- Bind loopback por padrão; `lan`/`tunnel` só quando você escolhe.
- Sem telemetria. Segredos só no `.env` (nunca commitado). DB local nunca versionado.
- Acesso remoto: **túnel privado** (Tailscale/WireGuard), nunca internet pública.

## Componente futuro: percepção em Rust (`src/`)

O runtime de percepção/cognição em Rust (`src/perception`, `src/cognition`, ...) é uma
camada **experimental e ainda não plugada**, pensada para presença ambiente de baixa
latência (óculos/carro). É bem testada isoladamente, mas não faz parte do caminho de
execução atual do kernel. Será integrada quando os corpos ambientes existirem.
