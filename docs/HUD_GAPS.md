# HUD GAPS — ARC vs kernel

> Levantado em 2026-08-14. O HUD servido é o **ARC** (`jarvis-ui/src/arc/`,
> canvas puro, sem framework — `index.html` aponta para `src/arc/main.js`).
> Este documento mapeia o que o kernel expõe (29 routers em
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
| `auth` | `security/Perms`, `network/Devices` (aparelhos pareados) + paleta `revogar aparelho <nome>` — **2026-08-15** |
| `automation` | `agents/*` (status, execuções, tipos) + paleta `rodar automação <slug>`, `ativar/desativar automação <slug>`, `instalar automações` (catálogo embutido) — **2026-08-15** |
| `briefing` | `projects/Timeline` (último briefing) + paleta `gerar briefing` — **2026-08-15** |
| `browser` | **novo router** — `browser/Tabs` (as buscas que o KERNEL fez desde o boot, efêmeras; cada `buscar`/`buscar e trazer` do vision vira uma aba) + `browser/Marks` (marcadores são memórias de tipo `bookmark`, vivem no grafo; paleta `marcar <url> <título>` / `desmarcar <título>`) via `GET /browser/tabs`, `GET/POST/DELETE /browser/marks` — **2026-08-15** |
| `chat` | conversas + `live.js` (chat, voz, visão) |
| `connectors` | `security/Keys` — capabilities vivas (método, categoria, ativo, params) + secrets do cofre — **2026-08-14** + paleta `chamar <capability> [chave=valor …]` (invoca a capability pelo kernel, resolvendo `{param}` e `{segredo.X}` no template) — **2026-08-15** |
| `decision` | `projects/Decision` (histórico: escolha, racional, data) + paleta `decidir foco` — **2026-08-14** |
| `directors` | `ai/Prompts`, `agents/Active` |
| `evals` | `ai/Evals` (casos + execuções) |
| `events` | `memory/Episodic` |
| `habits` | `files/Habits` (nome + streak) + paleta `marcar hábito <nome>` — **2026-08-14** |
| `health` | `ai/Models`, `network/Nodes`, heartbeat do reator |
| `journal` | `files/Journal` (anotações com humor e data) + paleta `anotar <texto>` — **2026-08-14** |
| `learning` | `ai/Learning` (total, qualidade média recente, lições) — **2026-08-14** |
| `memory` | `memory/*` (recentes, grafo, recall via paleta) + paleta `guardar <texto>` (POST /memory) e `esquecer <id|título>` (DELETE /memory/{id}) — **2026-08-15** |
| `network` | **novo router** — `network/Traffic` (contadores desde boot, velocidade medida entre leituras, interfaces por volume, conexões ativas por estado) via `GET /network/traffic` + `network/VPN` (interfaces de túnel no ar, rota padrão — heurística por nome de interface, declarada no `method`; o kernel mede, não conecta VPN) via `GET /network/vpn` — **2026-08-15** |
| `obsidian` | `files/*` (status do vault) + paleta `importar vault <caminho>`, `exportar vault <caminho>`, `observar vault [caminho]`, `parar observação` — **2026-08-15** |
| `optimize` | `system/Optimize` + paleta `medir otimização` (probe lento) e `otimizar completo` (varredura total: contexto, threads, batch, swap → lista de linhas de `.env`; o kernel só reporta, nunca edita) — **2026-08-15** |
| `planning` | `projects/*` (metas, quadro) + paleta `criar meta <título>`, `concluir meta <título>`, `progresso meta <título> <0-100>`, `cancelar meta <título>` (resolve pelo título, como o painel mostra) — **2026-08-15** |
| `radio` | `voice/Radio` (faixa atual, fila, volume, shuffle, repeat, adblock, **playlists** + stats) + paleta `tocar <busca>`, `volume <0-100>`, `pular faixa`, `tocar preset <n>` (corrigido: o regex genérico `tocar <busca>` engolia o comando), `colar <link>` (YouTube ou stream direto), `faixa anterior`, `limpar fila`, `buscar música <termo>`, `adicionar à fila <busca>`, `embaralhar`/`não embaralhar`, `repetir`/`não repetir`, `adblock ligar|desligar` + **playlists em memória** (como a fila): `salvar playlist <nome>` (snapshot da fila), `tocar playlist <nome>`, `playlists`, `apagar playlist <nome>` via `GET/POST/DELETE /radio/playlists…` — **2026-08-15** |
| `schedule` | `terminal/Jobs` + paleta `lembrar <texto> em <n> <min|h|d>` (com `repetir a cada`), `cancelar lembrete <id>` — **2026-08-14** |
| `security` | `security/*` completo — Threats/Audit/Keys + paleta `armar/desarmar honeypot`. **Exige sessão**: cofre e postura são `strict` (nunca aceitam o bypass) — `login <email> <senha>` na paleta guarda o JWT e toda request o apresenta |
| `system` | `system/*` (CPU, memória, disco, energia, temp) |
| `terminal` | **novo router** — `terminal/SSH` (status de sessões: porta 22 escutando + quem está conectado via `psutil.users()`, flag `remote`) via `GET /terminal/ssh`. **Fronteira declarada no payload**: o kernel reporta sessões; nunca abre shell, faz proxy ou encaminha porta — `terminal/Shell` continua `absent` por design (executar programa é da Teia, em automação revisada) — **2026-08-15** |
| `timetrack` | `system/Time` (timer aberto + tempo fechado por rótulo) + paleta `iniciar/parar timer <rótulo>` — **2026-08-14** |
| `vision` | status + câmera (`live.js`) + busca web (`vision/search`) |
| `voice` | `voice/*` + loop de voz (`live.js`) + **packs falam com voz TTS real** — cada pack carrega `tts_voice` (Edge neural: Jarvis Classic→Antonio, Amigável→Francisca), `tts_rate`, `tts_pitch` e `voice_profile` (clonagem VoiceBox: borgerth-jarvis, dondi-ultron, padua-alfred); `usar voz <nome>` reconfigura o synthesizer; **packs de personagem** (`ultron` = Márcio Dondi/James Spader, `alfred` = Pádua Moreira/Michael Caine) com `persona` injetada no system prompt do cérebro — o diálogo **aberto** (chat, stream, `/voice/chat`, `falar`) fala como o personagem, não só frases prontas; paleta `falar <texto>` via `/voice/speak` — **2026-08-15** |
| `world` | `ai/Context` (digest + perfil do dono + fatos do mundo) + paleta `definir/esquecer perfil <chave> [valor]`, `definir/esquecer fato <chave> [valor]` — curadoria soberana do modelo do dono — **2026-08-15** |

| `cortex` | **novo router — o cérebro simbólico (sem LLM)** — `POST /cortex/intent` (fala → intenção → ação nas engines reais, com `trace` da decisão e resposta honesta) + `GET /cortex/verbs` (a gramática que ele conhece). A paleta consulta o cortex **antes** do chat: texto que nenhum comando dinâmico casa vira `Jarvis: <fala>` → painel Cortex mostra verbo/alvo/resposta/trilha; `falar <texto>` sobe o áudio com a voz do pack ativo; `understood=false` lista o que ele sabe em vez de inventar. **Mic na paleta** (`#palMic`, Web Speech pt-BR): falou → transcreve → executa sozinho, mesmo caminho do teclado. **Camada de regras declarativas**: `backend-core/rules/*.yaml` (condição → ação, sem código arbitrário; `auto` controla propor vs executar) + `GET /cortex/rules` e `POST /cortex/rules/avaliar` (monta o snapshot do mundo e devolve decisões com a trilha condição por condição — o "por que decidi"); paleta `avaliar regras` e `regras` → painel Cortex · Regras — **2026-08-15** |

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

Leituras e escritas mapeadas — os 29 routers do kernel têm presença no ARC,
e as escritas principais saem da paleta (metas, memória, automações, vault,
rádio, mundo, capabilities, dispositivos, otimização, marcadores). Tráfego,
VPN, browser e SSH saíram das lacunas: agora são medidos de verdade.
A única lacuna `absent` restante é `terminal/Shell`, e é por design — nunca
shell por HTTP; executar programa é da Teia, em automação revisada.
Próximos passos naturais: validar os fluxos contra o kernel rodando e evoluir
o que o kernel ainda não mede.

## Verificação

`npm run check` em `jarvis-ui/` (smoke test: 61 submenus com leitura, 61 loaders
exercitados) — cada rota nova chamada por um loader precisa de stub em
`test/arc-smoke.mjs`, no shape real do router.
