# Roadmap — Sexta-Feira (kernel local e privado)

## Onde estamos (feito)

- ✅ Kernel local, dono único, 100% offline (Ollama). Sem nuvem, sem outro LLM.
- ✅ Autenticação do dono + **pareamento de dispositivos** (celular/carro/óculos/relógio).
- ✅ **Memória persistente** (SQLite + embeddings locais) injetada no raciocínio.
- ✅ Loop cognitivo: persona + memória + histórico → resposta (com streaming SSE).
- ✅ **Auto-aprendizado**: destila fatos duráveis após cada conversa.
- ✅ **Pipeline de ensino**: exportar história → dataset → fine-tuning LoRA → modelo seu no Ollama.
- ✅ Testes ponta a ponta (pytest) + degradação graciosa quando o cérebro está offline.
- ✅ App Android: login real, sessão, chat contra o kernel (URL configurável).
- ✅ Persistir o token no Android (DataStore) e auto-login (`SessionManager`).
- ✅ Streaming token-a-token no app (SSE via `/api/v1/chat/stream`).
- ✅ CI (GitHub Actions): pytest + lint + build Android a cada push.
- ✅ Hilt/DI no app + API client cobrindo os 24 endpoints do kernel.
- ✅ **Teia — plataforma de automação própria, em Python** (ADR-0013): orquestrador +
  operários, 44 tipos de nó, 5 gatilhos (cron/intervalo/evento/webhook/manual), trilha de
  execução por nó, API REST + CLI e 10 automações prontas. **O n8n foi removido** — não há
  mais runtime Node.js no projeto.

## Próximo (curto prazo)

- [ ] Tela de Configurações no Android: endereço do kernel + pareamento por código/QR.
- [ ] Curadoria de memória no app (ver/editar/esquecer o que ele sabe).
- [ ] Testes pytest para os routers novos (memory, schedule, action, connectors).

## Médio prazo

- [ ] Voz local: captura no app (SpeechRecognizer) + TTS local, sem nuvem.
- [ ] Ferramentas/ações locais (agenda, lembretes, dispositivos) com confirmação do dono.
- [ ] Migrações de schema (Alembic) e índice vetorial (sqlite-vec/FAISS) para memória grande.
- [ ] Agentes especializados (planejador, analista) roteados pelo cérebro.
- [ ] Teia — plugins por entry point (Fase 4): nós de terceiros como pacotes Python.
- [ ] Teia — editor visual no app, sobre `GET /api/v1/automations/types` (Fase 10 já expõe
      o schema de cada nó).

## Longo prazo (presença ambiente)

- [ ] Ligar o runtime de percepção em Rust (`src/`) como camada de baixa latência.
- [ ] Corpos ambientes: tela do carro, óculos, relógio — cada um pareado ao mesmo cérebro.
- [ ] Fine-tuning periódico automatizado (o cérebro "estuda" a própria história).
- [ ] Sincronização privada entre corpos via túnel (Tailscale/WireGuard).

## Fora de escopo (por decisão consciente)

- ❌ Qualquer conexão com LLM de nuvem.
- ❌ Multiusuário / cadastro público.
- ❌ Treinar um modelo de fronteira do zero (inviável e contra a privacidade).
