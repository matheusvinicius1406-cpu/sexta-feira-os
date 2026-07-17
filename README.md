# Sexta-Feira OS 🧠

**Seu segundo cérebro pessoal — local, privado e só seu.**

Sexta-Feira não é um chatbot de nuvem. É um *kernel cognitivo* que roda inteiramente
na sua máquina, no espírito de um Alfred / JARVIS: leal, íntimo e discreto. Ele
lembra do que importa, aprende com você e serve só a você. **Nenhuma palavra sua
sai deste host — não há OpenAI, Claude, Gemini nem qualquer LLM externo.**

## Princípios inegociáveis

- 🔒 **Local-only** — o raciocínio e os embeddings rodam via **Ollama**, na sua máquina. Zero nuvem.
- 👤 **Dono único** — uma só conta, sua. Sem cadastro aberto. Dispositivos são *pareados* por você.
- 🧩 **Multilocal (um cérebro, vários corpos)** — celular, tela do carro, óculos, relógio conectam ao mesmo cérebro pela sua rede privada.
- 💾 **Memória de verdade** — fatos, preferências e conversas persistem em SQLite com embeddings locais.
- 🕸️ **Grafo de conhecimento (estilo Obsidian)** — cada informação vira um *nó* que se **liga** às relacionadas (semântica + `[[wikilinks]]` + manual). O raciocínio percorre essas conexões: forma um cérebro em rede, não uma lista solta.
- 🤖 **Ele age sozinho** — do celular, por voz: "me lembra do dentista amanhã" → o cérebro decide e dispara a automação/ação/lembrete certo (tool-calling), sem terminal.
- ⏰ **Ele lembra na hora certa** — agenda lembretes e ações no tempo ("me lembra disso daqui a 2 meses") e dispara sozinho quando chega a hora.
- 🔌 **Ele executa (quase) tudo** — um sistema de **conectores de API**: você cadastra capacidades (uma vez), o cérebro as chama pelo nome. Chaves de API ficam **criptografadas** e o cérebro só chama o que você definiu (sem URL arbitrária).
- 📚 **Ele aprende com você** — sua história vira dataset para *fine-tuning* (LoRA); o modelo fica cada vez mais *seu*.
- 🕵️ **Sem telemetria** — nada é rastreado, nada é enviado.

## Como funciona (arquitetura)

```
  Corpos (celular, carro, óculos, relógio, desktop)
        │  HTTP privado (LAN / túnel WireGuard) — nunca internet pública
        ▼
  ┌─────────────────────── KERNEL (sua máquina) ───────────────────────┐
  │  FastAPI  →  Cognition  →  LocalBrain ──► Ollama (raciocínio+embed) │
  │                  │                                                   │
  │                  └─► PersistentMemory ──► SQLite (segundo cérebro)   │
  └────────────────────────────────────────────────────────────────────┘
        │  quando você quiser ensiná-lo:
        ▼
  export_training_data.py → dataset.jsonl → finetune_lora.py → modelo SEU no Ollama
```

O único backend de inferência é o **Ollama local**. Se um dia você treinar o seu
próprio modelo, basta apontar `BRAIN_MODEL` para ele — nada mais muda.

## Início rápido

```bash
# 1. Ollama (o cérebro local) — instala e roda 100% na sua máquina
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
ollama pull nomic-embed-text

# 2. Kernel
cp .env.template .env          # edite OWNER_EMAIL / OWNER_PASSWORD / DEVICE_PAIRING_CODE
cd backend-core
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main             # http://127.0.0.1:8000

# 3. Conversar
curl -s localhost:8000/api/v1/health
# login → pegue o token → POST /api/v1/chat {"message": "..."}
```

Ou use `scripts/setup.sh` para fazer tudo isso de uma vez.

## API (v1)

| Método | Rota | O quê |
|---|---|---|
| `GET` | `/api/v1/health` | status + se o cérebro está online |
| `POST` | `/api/v1/auth/login` | login do dono (email+senha) |
| `POST` | `/api/v1/auth/devices/pair` | parear um corpo (celular/carro/óculos/relógio) |
| `GET` | `/api/v1/auth/devices` | listar/gerir dispositivos pareados |
| `POST` | `/api/v1/chat` | conversar (com memória + histórico) |
| `POST` | `/api/v1/chat/stream` | conversar em streaming (SSE) |
| `POST` | `/api/v1/memory` | ensinar um fato (auto-liga aos relacionados; aceita `[[wikilinks]]`) |
| `POST` | `/api/v1/memory/recall` | recall em rede (semântico + expansão pelo grafo) |
| `GET`/`DELETE` | `/api/v1/memory[/{id}]` | revisar / esquecer |
| `POST` | `/api/v1/memory/{id}/link` | conectar dois nós manualmente |
| `GET` | `/api/v1/memory/{id}/neighbours` | ligações + backlinks de um nó |
| `GET` | `/api/v1/memory/graph` | o grafo inteiro (nós + arestas) para visualizar |
| `POST` | `/api/v1/voice/transcribe` | áudio → texto (STT local, offline) |
| `POST` | `/api/v1/voice/speak` | texto → áudio (TTS local, offline) |
| `POST` | `/api/v1/voice/chat` | áudio → ouve, pensa (com memória) e responde (voz) |
| `GET` | `/api/v1/automations` | lista seus workflows do n8n |
| `POST` | `/api/v1/automations/trigger` | dispara um workflow (o Sexta-Feira **age**) |
| `GET` | `/api/v1/automations/status` | o n8n local está no ar? |
| `POST` | `/api/v1/actions/dispatch` | manda um corpo (celular/PC) executar uma ação |
| `WS` | `/api/v1/actions/stream?token=…` | canal ao vivo do dispositivo (recebe ações, reporta) |
| `GET` | `/api/v1/actions/pending` | fila do dispositivo (fallback por polling) |
| `POST` | `/api/v1/actions/{id}/result` | o dispositivo reporta o resultado |
| `POST` | `/api/v1/schedule` | agenda um lembrete ou ação futura |
| `GET`/`DELETE` | `/api/v1/schedule[/{id}]` | lista / cancela agendamentos |
| `POST`/`GET` | `/api/v1/connectors` | cadastra / lista **capacidades de API** (o cérebro executa qualquer coisa) |
| `POST` | `/api/v1/connectors/{name}/call` | executa uma capacidade |
| `POST`/`GET` | `/api/v1/connectors/secrets` | guarda chaves de API **criptografadas** (só nomes são lidos) |

### Voz local (offline)

Ouvir e falar rodam na sua máquina. É um extra opcional (degrada com 503 limpo se ausente):

```bash
pip install -r backend-core/requirements-voice.txt   # faster-whisper + piper
# baixe uma voz Piper pt-BR (.onnx) e aponte TTS_VOICE no .env
```

### Automações (as mãos — n8n local)

O Sexta-Feira **age** através de um **n8n self-hosted** (centenas de integrações →
milhares de automações). Tudo roda na sua máquina.

```bash
docker compose up -d n8n     # painel em http://127.0.0.1:5678 (só seu)
# crie workflows com um nó Webhook; o kernel dispara por /api/v1/automations/trigger
# para listar workflows, gere uma API key no n8n e coloque em N8N_API_KEY no .env
```

> Privacidade: o motor n8n é local. Uma automação que fala com um serviço externo
> (enviar e-mail, etc.) o faz por sua escolha naquele fluxo — não é vazamento do cérebro.

## Ensinar o Sexta-Feira (fine-tuning)

O que torna a IA *sua* não é o tamanho — é **seus dados + sua memória + sua voz**.
Loop de aprendizado (offline, numa máquina com GPU):

1. Viva com o kernel: converse e ensine fatos (`POST /api/v1/memory`).
2. `python scripts/export_training_data.py` → gera `data/dataset.jsonl` a partir da SUA história.
3. `python scripts/finetune_lora.py` → treina um *adapter* LoRA sobre um modelo aberto.
4. Exporte para GGUF, `ollama create sexta`, e ponha `BRAIN_MODEL=sexta` no `.env`.

> Sobre "criar minha IA de 500B do zero": treinar um modelo de fronteira do zero custa
> dezenas de milhões e exige data-center — o que quebraria sua privacidade. O caminho
> real e privado é **partir de um modelo aberto e especializá-lo nos seus dados**. Você
> já roda, localmente, um modelo com bilhões de parâmetros; o fine-tuning o torna seu.

## Estrutura

```
backend-core/app/
  brain/        engine.py (Ollama)  memory.py (2º cérebro)  cognition.py (loop)  teach.py (dataset)
  api/routers/  health  auth(login+pareamento)  chat  memory
  auth/  core/  db/  models/
backend-core/tests/    testes ponta a ponta (pytest)
scripts/        setup.sh  export_training_data.py  finetune_lora.py
mobile-android/ app cliente (um dos "corpos")
src/            [experimental] runtime de percepção em Rust p/ ambiente (óculos/carro) — futuro, ainda não plugado
```

## Privacidade & acesso remoto

Padrão = `loopback` (só esta máquina). Para usar do celular/carro em casa, `ACCESS_MODE=lan`.
Para te acompanhar fora de casa **sem** expor à internet pública, use um túnel privado
(**Tailscale/WireGuard**) e `ACCESS_MODE=tunnel`. O kernel nunca deve ficar aberto na web.

## Licença

MIT — veja [LICENSE](./LICENSE). É seu. Use como quiser.
