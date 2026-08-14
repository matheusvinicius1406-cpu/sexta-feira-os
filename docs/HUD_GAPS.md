# HUD GAPS — ARC vs kernel

> Levantado em 2026-08-14. O HUD servido é o **ARC** (`jarvis-ui/src/arc/`,
> canvas puro, sem framework — `index.html` aponta para `src/arc/main.js`).
> Este documento mapeia o que o kernel expõe (26 routers em
> `backend-core/app/api/routers/`) contra o que o ARC lê, e prioriza as lacunas.

## Regra do HUD (herdada de `kernel.js`)

Um painel mostra uma medição ou mostra **por que não há nenhuma**. Capacidade
que o kernel não tem é declarada `absent` com o motivo — nunca inventar número
para o painel acender.

## ✅ Já ligado no ARC

| Router do kernel | Painéis / leituras no ARC |
|---|---|
| `auth` | `security/Perms`, `network/Devices` (aparelhos pareados) |
| `automation` | `agents/*` (status, execuções, tipos, rodar) |
| `briefing` | `projects/Timeline` (último briefing + gerar) |
| `chat` | conversas + `live.js` (chat, voz, visão) |
| `connectors` | `security/Keys` (**só secrets**; capabilities não) |
| `directors` | `ai/Prompts`, `agents/Active` |
| `evals` | `ai/Evals` (casos + execuções) |
| `events` | `memory/Episodic` |
| `health` | `ai/Models`, `network/Nodes`, heartbeat do reator |
| `memory` | `memory/*` (recentes, grafo, recall via paleta) |
| `obsidian` | `files/*` (status do vault) |
| `planning` | `projects/*` (metas, quadro) |
| `schedule` | `terminal/Jobs` (**leitura** — sem criar/cancelar) |
| `security` | `security/*` completo — Threats/Audit/Keys + paleta `armar/desarmar honeypot` |
| `system` | `system/*` (CPU, memória, disco, energia, temp) |
| `vision` | status + câmera (`live.js`) + busca web (`vision/search`) |
| `voice` | `voice/*` + loop de voz (`live.js`) |
| `world` | `ai/Context` (digest), briefing, `world/*` no kernel |

## 🔴 Lacunas sem nenhuma presença no ARC

| Área | Endpoints do kernel | Valor / como entra |
|---|---|---|
| **Agente (Pulse)** | `GET /agent/pulse`, `POST /agent/pulse/run`, `GET /agent/proposals`, `POST /proposals/{id}/approve\|reject` | **Portão de confirmação**: ver o que o agente quer fazer e aprovar/recusar. Entra como sub-item de `Agents` — sem redesenho |
| **Otimizador** | `GET /optimize`, `POST /optimize/probe\|context\|threads\|embedding-batch\|swap\|full` | Mede a inferência real e **devolve a linha de .env** (o dono decide; nunca escreve). Painel de leitura puro |
| **Decision** | `GET /decision`, `GET /decision/next`, `GET /decision/{id}` | Por que o kernel escolheu o próximo objetivo (fundamenta o Foco do briefing) |
| **Rádio** | `GET/POST /radio` (play, youtube, volume, skip…) | Mídia controlada pelo kernel; menor valor imediato |
| **Ações pendentes** | `GET /actions/pending`, `POST /actions/dispatch`, `POST /actions/{id}/result` | Comandos que o kernel mandou aos corpos + resultados. Casa com `network/Devices` |
| **Schedule (escrita)** | `POST/DELETE /schedule` | Criar/cancelar lembretes da UI (hoje `terminal/Jobs` só lê) |

## 🟡 Exports mortos no `api.js` do ARC

Existem no `src/arc/api.js` mas **nenhum módulo lê** (o smoke test até stuba as
rotas):

| Export | Rota | Decisão pendente |
|---|---|---|
| `journal`, `habits` | `/journal`, `/habits` | Virar painéis (módulo Journal?) ou remover |
| `timeSummary` | `/time/summary` | Virar painel (sub-item de `System`?) ou remover |
| `learningStats`, `learnings` | `/learning/stats`, `/learning` | Virar painel (sub-item de `AI`?) ou remover |

## 🟢 Nota de arquitetura

Os **12 módulos** do ARC são fixos por design (`docs/design-system/`). Estender
o desenho radial (novo módulo) é decisão de design; sub-itens em módulos
existentes não tocam no desenho:

- Pulse → `Agents` (novo sub-item)
- Otimizador → `System` (novo sub-item)
- Learning → `AI`
- Time → `System`
- Journal/Habits → `Files` ou módulo novo
- Schedule escrita → comando de paleta + `terminal/Jobs`

## Ordem sugerida

1. **Pulse/Propostas** — portão de confirmação, alto valor, entra em `Agents` sem redesenho
2. **Otimizador** — mede e sugere `.env`; painel de leitura puro
3. **Schedule escrita** — criar/cancelar lembretes do HUD (paleta)
4. **Journal/Habits + Time** — decidir: painéis ou remover exports mortos
5. **Decision, Radio, Actions** — leitura; menor valor imediato

## Verificação

`npm run check` em `jarvis-ui/` (smoke test: 51 submenus com leitura, 51 loaders
exercitados) — cada rota nova chamada por um loader precisa de stub em
`test/arc-smoke.mjs`, no shape real do router.
