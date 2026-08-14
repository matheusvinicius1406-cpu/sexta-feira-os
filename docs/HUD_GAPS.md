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
| `agent` (pulse) | `agents/Pulse` (status + último ciclo) e `agents/Proposals` (portão de confirmação) + paleta `rodar pulse`, `aprovar/recusar <id>` — **2026-08-14** |
| `action` | `network/Actions` (histórico de comandos aos corpos: ação, params, aparelho, status, erro, hora) + paleta `comandar <aparelho> <ação>` — **2026-08-14** |
| `auth` | `security/Perms`, `network/Devices` (aparelhos pareados) |
| `automation` | `agents/*` (status, execuções, tipos, rodar) |
| `briefing` | `projects/Timeline` (último briefing + gerar) |
| `chat` | conversas + `live.js` (chat, voz, visão) |
| `connectors` | `security/Keys` (**só secrets**; capabilities não) |
| `decision` | `projects/Decision` (histórico: escolha, racional, data) + paleta `decidir foco` — **2026-08-14** |
| `directors` | `ai/Prompts`, `agents/Active` |
| `evals` | `ai/Evals` (casos + execuções) |
| `events` | `memory/Episodic` |
| `habits` | `files/Habits` (nome + streak) + paleta `marcar hábito <nome>` — **2026-08-14** |
| `health` | `ai/Models`, `network/Nodes`, heartbeat do reator |
| `journal` | `files/Journal` (anotações com humor e data) + paleta `anotar <texto>` — **2026-08-14** |
| `learning` | `ai/Learning` (total, qualidade média recente, lições) — **2026-08-14** |
| `memory` | `memory/*` (recentes, grafo, recall via paleta) |
| `obsidian` | `files/*` (status do vault) |
| `optimize` | `system/Optimize` + paleta `medir otimização` (probe lento que devolve a linha de `.env`) — **2026-08-14** |
| `planning` | `projects/*` (metas, quadro) |
| `radio` | `voice/Radio` (faixa atual, fila, volume, shuffle, repeat, adblock) + paleta `tocar <busca>`, `volume <0-100>`, `pular faixa`, `tocar preset <n>` — **2026-08-14** |
| `schedule` | `terminal/Jobs` + paleta `lembrar <texto> em <n> <min|h|d>` (com `repetir a cada`), `cancelar lembrete <id>` — **2026-08-14** |
| `security` | `security/*` completo — Threats/Audit/Keys + paleta `armar/desarmar honeypot` |
| `system` | `system/*` (CPU, memória, disco, energia, temp) |
| `timetrack` | `system/Time` (timer aberto + tempo fechado por rótulo) + paleta `iniciar/parar timer <rótulo>` — **2026-08-14** |
| `vision` | status + câmera (`live.js`) + busca web (`vision/search`) |
| `voice` | `voice/*` + loop de voz (`live.js`) |
| `world` | `ai/Context` (digest), briefing, `world/*` no kernel |

## 🔴 Lacunas sem nenhuma presença no ARC

| Área | Endpoints do kernel | Valor / como entra |
|---|---|---|
| **Connectors (capabilities)** | `GET /connectors` (capabilities dos conectores) | Hoje `security/Keys` só mostra secrets; as capabilities vivas ficam de fora |

## 🟢 Nota de arquitetura

Os **12 módulos** do ARC são fixos por design (`docs/design-system/`). Estender
o desenho radial (novo módulo) é decisão de design; sub-itens em módulos
existentes não tocam no desenho — como já foi feito:

- ✅ Pulse → `Agents` (`Pulse` + `Proposals`)
- ✅ Otimizador → `System` (`Optimize`)
- ✅ Journal/Habits → `Files` (`Journal`, `Habits`)
- ✅ Time → `System` (`Time`)
- ✅ Learning → `AI` (`Learning`)
- ✅ Decision → `Projects` (`Decision`)
- ✅ Rádio → `Voice` (`Radio`)
- ✅ Schedule escrita → comando de paleta + `terminal/Jobs`
- ✅ Actions → `Network` (`Actions`)

## Ordem sugerida

Nenhuma lacuna de router restante — só a leitura de capabilities de conectores
(`GET /connectors`) como enriquecimento de `security/Keys`.

## Verificação

`npm run check` em `jarvis-ui/` (smoke test: 61 submenus com leitura, 61 loaders
exercitados) — cada rota nova chamada por um loader precisa de stub em
`test/arc-smoke.mjs`, no shape real do router.
