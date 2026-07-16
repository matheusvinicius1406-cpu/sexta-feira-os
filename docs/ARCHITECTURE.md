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
