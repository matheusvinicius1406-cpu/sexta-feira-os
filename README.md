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
| `POST` | `/api/v1/memory` | ensinar um fato ao cérebro |
| `POST` | `/api/v1/memory/recall` | buscar na memória (semântico) |
| `GET`/`DELETE` | `/api/v1/memory[/{id}]` | revisar / esquecer |

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
