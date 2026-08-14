/**
 * What each module's panel shows, and where it comes from.
 *
 * One entry per sub-item of the twelve modules in `main.js`. Each entry is a
 * `load()` that returns rows the panel renders — nothing here formats pixels,
 * and nothing here holds state.
 *
 * The hard rule, carried over from `kernel.js`: a panel shows a measurement or
 * it shows why there is none. Several sub-items in the ARC design describe
 * capabilities this OS does not have — SSH, VPN, browser tabs, threat feeds.
 * Those are declared `absent`, with the reason, and the panel says so plainly.
 * The alternative was to invent an endpoint per label so every panel would
 * light up, which would mean twelve modules of decoration and no way for the
 * owner to tell which parts of their own system are real.
 *
 * A loader either returns `{ rows }` (optionally `{ rows, note }`) or throws a
 * KernelError, which the panel renders as the failure it was.
 */
import * as api from './api.js'

/** Row helper: a labelled value. `null`/`undefined`/'' become an em dash. */
const row = (k, v) => ({ k, v: v === null || v === undefined || v === '' ? '—' : String(v) })

/** Declares a capability this kernel genuinely does not have. */
const absent = (why) => ({ absent: why })

const bytes = (n) => {
  if (typeof n !== 'number' || !isFinite(n)) return '—'
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i += 1 }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${u[i]}`
}

const pct = (n) => (typeof n === 'number' ? `${n.toFixed(1)} %` : '—')

const duration = (s) => {
  if (typeof s !== 'number' || s < 0) return '—'
  const d = Math.floor(s / 86400)
  const h = Math.floor(s / 3600) % 24
  const m = Math.floor(s / 60) % 60
  return d > 0 ? `${d}d ${h}h ${m}m` : h > 0 ? `${h}h ${m}m` : `${m}m`
}

const when = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? String(iso) : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Turn a list into rows, saying so when the list is legitimately empty. */
const listing = (items, toRow, emptyNote) =>
  items.length ? { rows: items.map(toRow) } : { rows: [], note: emptyNote }

const truncate = (s, n = 88) => {
  const t = String(s ?? '').replace(/\s+/g, ' ').trim()
  return t.length > n ? `${t.slice(0, n - 1)}…` : t
}

export const PANELS = {
  // ── AI: the brain itself ───────────────────────────────────
  'ai/Models': async () => {
    const [h, v] = await Promise.all([api.health(), api.visionStatus().catch(() => null)])
    return {
      rows: [
        row('Brain model', h.brain_model),
        row('Brain online', h.brain_online ? 'sim' : 'não'),
        row('Kernel', `${h.app} ${h.version}`),
        row('Access mode', h.access_mode),
        row('Vision model', v?.model ?? v?.vision_model),
        row('Vision online', v ? (v.available ?? v.healthy ? 'sim' : 'não') : '—'),
      ],
    }
  },
  'ai/Prompts': async () => {
    const ds = await api.directors()
    return listing(
      ds,
      (d) => row(d.name ?? d.slug, truncate(d.mandate ?? d.role ?? d.description)),
      'nenhum diretor definido — cada um carrega o próprio mandato/prompt',
    )
  },
  'ai/Context': async () => {
    const d = await api.worldDigest()
    const text = typeof d === 'string' ? d : (d.digest ?? JSON.stringify(d))
    return {
      rows: String(text).split('\n').filter(Boolean).map((line, i) => row(`#${i + 1}`, line)),
      note: 'o digest que o kernel injeta em cada conversa',
    }
  },
  'ai/Tuning': async () => {
    const h = await api.health()
    return {
      rows: [row('Brain model', h.brain_model), row('Access mode', h.access_mode)],
      note: 'temperatura e amostragem vivem no .env do kernel; não há endpoint de escrita',
    }
  },
  'ai/Evals': async () => {
    const [cases, runs] = await Promise.all([api.evalCases(), api.evalRuns().catch(() => [])])
    return {
      rows: [
        row('Casos', cases.length),
        row('Execuções', runs.length),
        ...runs.slice(0, 6).map((r) => row(when(r.created_at), `${r.passed ?? '—'}/${r.total ?? '—'}`)),
      ],
    }
  },
  'ai/Learning': async () => {
    const [xs, st] = await Promise.all([api.learnings(), api.learningStats().catch(() => null)])
    return {
      rows: [
        row('Aprendizados', st?.total ?? xs.length),
        row('Qualidade média (recentes)', st?.recent_avg_quality ?? '—'),
        ...xs.slice(0, 10).map((x) => row(when(x.created_at), truncate(x.lesson || x.context))),
      ],
      note: xs.length
        ? 'lições destiladas de conversas e resultados'
        : 'nenhuma lição registrada ainda — o kernel aprende sozinho com o tempo',
    }
  },

  // ── Memory ─────────────────────────────────────────────────
  'memory/Recent': async () => {
    const ms = await api.memories()
    return listing(
      ms.slice(0, 12),
      (m) => row(m.kind ?? 'fact', truncate(m.title || m.content)),
      'nenhuma memória gravada ainda',
    )
  },
  'memory/Semantic': async () => {
    const g = await api.memoryGraph()
    return {
      rows: [
        row('Nós', g.nodes?.length ?? 0),
        row('Ligações', g.links?.length ?? g.edges?.length ?? 0),
        ...(g.nodes ?? []).slice(0, 8).map((n) => row(n.kind ?? 'nó', truncate(n.title))),
      ],
      note: 'busca semântica: use a paleta (Ctrl+K) e digite uma consulta',
    }
  },
  'memory/Episodic': async () => {
    const es = await api.events()
    return listing(
      es.slice(0, 12),
      (e) => row(when(e.created_at), e.type),
      'nenhum evento registrado ainda',
    )
  },
  'memory/Purge': async () => {
    const ms = await api.memories()
    return {
      rows: [row('Memórias', ms.length)],
      note: 'apagar é destrutivo e definitivo: feito por memória, via DELETE /memory/{id}',
    }
  },

  // ── Agents: directors + the Teia + o Pulse ─────────────────
  'agents/Pulse': async () => {
    const p = await api.pulseStatus()
    if (!p.enabled) {
      return {
        rows: [row('Agente', 'desligado')],
        note: 'AGENT_PULSE_ENABLED=false no .env — ligue para o kernel pensar sozinho',
      }
    }
    const r = p.last_report ?? {}
    return {
      rows: [
        row('Agente', 'ativo'),
        row('Propostas pendentes', p.pending_proposals ?? 0),
        row('Último ciclo', r.reason ?? '—'),
        row('Percebeu', (r.noticed ?? []).length),
        row('Executou', (r.executed ?? []).length),
        row('Propôs', (r.proposed ?? []).length),
        row('Pulou', (r.skipped ?? []).length),
      ],
      note: 'rodar um ciclo agora: paleta `rodar pulse`',
    }
  },
  'agents/Proposals': async () => {
    const ps = await api.proposals()
    return listing(
      ps.slice(0, 12),
      (p) =>
        row(
          truncate(p.title ?? p.id, 40),
          `${p.kind ?? '?'} · ${p.status ?? '?'} · ${String(p.id ?? '').slice(0, 8)}`,
        ),
      'nenhuma proposta — o agente não está pedindo nada agora',
    )
  },
  'agents/Active': async () => {
    const [ds, st] = await Promise.all([api.directors(), api.automationStatus().catch(() => null)])
    return {
      rows: [
        row('Diretores', ds.length),
        row('Automações armadas', st?.armed ?? st?.enabled ?? '—'),
        row('Em execução', st?.running ?? '—'),
        ...ds.slice(0, 8).map((d) => row(d.name ?? d.slug, d.role ?? d.specialty ?? '—')),
      ],
    }
  },
  'agents/Queue': async () => {
    const xs = await api.executions()
    const items = Array.isArray(xs) ? xs : (xs.items ?? [])
    return listing(
      items.slice(0, 12),
      (x) => row(x.workflow_id ?? x.slug ?? x.id, `${x.status} · ${when(x.started_at ?? x.created_at)}`),
      'nenhuma execução na fila',
    )
  },
  'agents/Registry': async () => {
    const t = await api.automationTypes()
    const nodes = t.nodes ?? t.node_types ?? []
    const triggers = t.triggers ?? t.trigger_types ?? []
    return {
      rows: [
        row('Tipos de nó', nodes.length),
        row('Tipos de gatilho', triggers.length),
        row('Gatilhos', triggers.join(', ')),
      ],
      note: `nós: ${nodes.join(', ')}`,
    }
  },
  'agents/Logs': async () => {
    const xs = await api.executions()
    const items = Array.isArray(xs) ? xs : (xs.items ?? [])
    const failed = items.filter((x) => x.status && x.status !== 'sucesso' && x.status !== 'success')
    return listing(
      failed.slice(0, 12),
      (x) => row(x.workflow_id ?? x.id, `${x.status}${x.error ? ` · ${truncate(x.error, 60)}` : ''}`),
      'nenhuma execução com falha',
    )
  },
  'agents/Spawn': async () => {
    const as = await api.automations()
    return listing(
      as.slice(0, 12),
      (a) => row(a.slug ?? a.name, a.enabled ? 'armada' : 'desarmada'),
      'nenhuma automação instalada — instale o catálogo pela API',
    )
  },

  // ── Files / vault ──────────────────────────────────────────
  'files/Recent': async () => {
    const s = await api.obsidianStatus()
    return {
      rows: [
        row('Vault', s.vault_path),
        row('Configurado', s.default_path_configured ? 'sim' : 'não'),
        row('Observando', s.watching ? 'sim' : 'não'),
        row('Notas', s.note_count ?? s.notes ?? '—'),
      ],
    }
  },
  'files/Index': async () => {
    const g = await api.memoryGraph()
    return {
      rows: [row('Nós indexados', g.nodes?.length ?? 0), row('Ligações', g.links?.length ?? 0)],
      note: 'o índice do vault é o próprio grafo de memória',
    }
  },
  'files/Vault': async () => {
    const s = await api.obsidianStatus()
    return { rows: Object.entries(s).map(([k, v]) => row(k, typeof v === 'object' ? JSON.stringify(v) : v)) }
  },
  'files/Journal': async () => {
    const es = await api.journal()
    return listing(
      es.slice(0, 15),
      (e) => row(when(e.created_at), `${e.mood ? `[${e.mood}] ` : ''}${truncate(e.content)}`),
      'nenhuma anotação — escreva uma: paleta `anotar <texto>`',
    )
  },
  'files/Habits': async () => {
    const hs = await api.habits()
    return listing(
      hs,
      (h) => row(h.name, `${h.streak ?? 0} dia(s)`),
      'nenhum hábito — marque um: paleta `marcar hábito <nome>`',
    )
  },
  'files/Sync': async () => {
    const s = await api.obsidianStatus()
    return {
      rows: [row('Vault', s.vault_path), row('Observando', s.watching ? 'sim' : 'não')],
      note: 'importar/exportar escrevem no seu disco: disparados explicitamente, nunca por abrir um painel',
    }
  },

  // ── Projects: planning ─────────────────────────────────────
  'projects/Active': async () => {
    const gs = await api.goals()
    const open = gs.filter((g) => ['pending', 'active', 'blocked'].includes(g.status))
    return listing(
      open,
      (g) => row(truncate(g.title, 44), `${g.status} · ${Math.round((g.progress ?? 0) * 100)}%`),
      'nenhuma meta aberta',
    )
  },
  'projects/Archive': async () => {
    const gs = await api.goals()
    const done = gs.filter((g) => ['done', 'completed', 'cancelled'].includes(g.status))
    return listing(done, (g) => row(truncate(g.title, 44), g.status), 'nada arquivado ainda')
  },
  'projects/Tasks': async () => {
    const b = await api.board()
    const cols = Object.entries(b ?? {})
    return listing(
      cols,
      ([name, items]) => row(name, Array.isArray(items) ? items.length : String(items)),
      'quadro vazio',
    )
  },
  'projects/Decision': async () => {
    const hs = await api.decisionHistory()
    return listing(
      hs.slice(0, 12),
      (d) =>
        row(
          truncate(d.chosen_label ?? d.question ?? d.id, 40),
          `${truncate(d.rationale ?? '', 44)} · ${when(d.created_at)}`,
        ),
      'nenhuma decisão registrada — `decidir foco` escolhe o próximo objetivo',
    )
  },
  'projects/Timeline': async () => {
    const b = await api.briefingLatest().catch(() => null)
    if (!b) return { rows: [], note: 'nenhum briefing gerado ainda' }
    return {
      rows: String(b.summary ?? '').split('\n').filter(Boolean).map((l, i) => row(`#${i + 1}`, l)),
      note: `briefing de ${when(b.created_at)}`,
    }
  },

  // ── Terminal ───────────────────────────────────────────────
  'terminal/Shell': async () =>
    absent(
      'este kernel não expõe shell por HTTP. Executar programa é capacidade da Teia ' +
      '(nó "programa"), dentro de uma automação revisada — não um prompt aberto na rede.',
    ),
  'terminal/History': async () => {
    const xs = await api.executions()
    const items = Array.isArray(xs) ? xs : (xs.items ?? [])
    return listing(
      items.slice(0, 15),
      (x) => row(when(x.started_at ?? x.created_at), `${x.workflow_id ?? x.id} · ${x.status}`),
      'nenhuma execução registrada',
    )
  },
  'terminal/Jobs': async () => {
    const ts = await api.schedule()
    return listing(
      ts,
      (t) => row(truncate(t.text ?? t.id, 40), `${t.kind ?? '?'} · ${t.status ?? '?'} · ${when(t.due_at)}`),
      'nenhuma tarefa agendada — crie uma: paleta `lembrar <texto> em <n> <min|h|d>`',
    )
  },
  'terminal/SSH': async () =>
    absent('o kernel não fala SSH. Ele roda na sua máquina; não há sessão remota a listar.'),

  // ── Browser: the kernel's reach into the web ───────────────
  'browser/Tabs': async () =>
    absent('o kernel não controla um navegador. O alcance dele à web é busca, em Research.'),
  'browser/Research': async () => ({
    rows: [],
    note: 'busca web: abra a paleta (Ctrl+K) e digite `buscar <termo>`',
  }),
  'browser/Capture': async () => ({
    rows: [],
    note: 'buscar e trazer o conteúdo do melhor resultado: paleta (Ctrl+K), `buscar <termo>`',
  }),
  'browser/Marks': async () =>
    absent('não há favoritos: o que vale ser guardado vira memória, em Memory.'),

  // ── Security (defesa ativa) ────────────────────────────────
  'security/Keys': async () => {
    // Capabilities (o que o kernel pode chamar) + secrets (nomes do cofre;
    // valores nunca saem do kernel). A API de secrets responde {"names": [...]}.
    const [cs, ss] = await Promise.all([
      api.connectors().catch(() => []),
      api.secrets().catch(() => ({ names: [] })),
    ])
    const names = Array.isArray(ss) ? ss : (ss.names ?? ss.secrets ?? [])
    const capRows = (cs ?? []).map((c) => row(
      `${c.method ?? '?'} ${c.name}`,
      `${c.category ?? 'general'} · ${c.enabled ? 'ativo' : 'desligado'}${(c.params ?? []).length ? ` · ${c.params.length} param(s)` : ''}`,
    ))
    const secretRows = names.map((s) => {
      const n = typeof s === 'string' ? s : (s.name ?? '—')
      const isBait = String(n).toLowerCase().startsWith('honeypot.')
      return row(n, isBait ? '🪤 isca armada — ler dispara alerta' : 'guardado no cofre')
    })
    return {
      rows: [...capRows, ...secretRows],
      note: !capRows.length && !secretRows.length
        ? 'nenhuma capability nem segredo — arme uma isca pela paleta: “armar honeypot <nome>”'
        : !secretRows.length
          ? 'nenhum segredo no cofre — arme uma isca pela paleta: “armar honeypot <nome>”'
          : undefined,
    }
  },
  'security/Audit': async () => {
    const a = await api.securityAudit()
    const d = a.defesas ?? {}
    const rl = d.rate_limit ?? {}
    const ng = d.netguard ?? {}
    const rows = [
      row('Acesso', a.acesso?.access_mode),
      row('Bypass dev', a.acesso?.auth_dev_bypass ? 'LIGADO ⚠️ desligue no .env' : 'desligado'),
      row('Honeypots armados', d.honeypots_armados),
      row('Netguard (SSRF)', ng.ativo ? 'ativo' : 'desligado'),
      row('Hosts internos permitidos', (ng.hosts_internos_permitidos ?? '').trim() || 'nenhum'),
      row('Rate limit', `${rl.max_tentativas ?? '?'} tentativas / ${rl.janela_segundos ?? '?'}s`),
      row('Lockout', `${rl.lockout_segundos ?? '?'}s`),
      row('IPs bloqueados agora', rl.ips_bloqueados_agora ?? 0),
      row('Ameaças no total', a.ameacas?.total ?? 0),
    ]
    const recs = (a.recomendacoes ?? []).filter(Boolean)
    return { rows, note: recs.length ? recs.join(' · ') : 'tudo em ordem — nenhuma recomendação pendente' }
  },
  'security/Perms': async () => {
    const [ds, h] = await Promise.all([api.devices(), api.health()])
    const authed = api.hasToken()
    return {
      rows: [
        row('Access mode', h.access_mode),
        row('Sessão', authed ? 'token de dono presente' : 'sem token — cofre e postura exigem `login <email> <senha>`'),
        row('Aparelhos pareados', ds.length),
        ...ds.map((d) => row(d.name ?? d.id, d.revoked ? 'revogado' : 'ativo')),
      ],
    }
  },
  'security/Threats': async () => {
    const ts = await api.securityThreats(30)
    return listing(
      ts,
      (t) => {
        const type = String(t.type ?? '?').replace(/^threat\./, '')
        const ip = t.source_ip || '—'
        return row(`${type} · ${ip} · ${when(t.at)}`, truncate(t.detail ?? ''))
      },
      'nenhuma ameaça registrada — nenhum tripwire disparou',
    )
  },

  // ── Voice ──────────────────────────────────────────────────
  'voice/Listen': async () => {
    const s = await api.voiceStatus()
    return {
      rows: Object.entries(s).map(([k, v]) => row(k, typeof v === 'object' ? JSON.stringify(v) : v)),
      note: 'segure V para falar com o Jarvis; solte para ele responder',
    }
  },
  'voice/Voices': async () => {
    const ps = await api.voicePacks()
    const packs = Array.isArray(ps) ? ps : (ps.packs ?? [])
    return listing(
      packs,
      (p) => row(typeof p === 'string' ? p : (p.name ?? '—'), typeof p === 'object' ? (p.description ?? '') : ''),
      'nenhum pacote de voz instalado',
    )
  },
  'voice/Phrases': async () => {
    const p = await api.voicePersonality()
    return { rows: Object.entries(p).map(([k, v]) => row(k, typeof v === 'object' ? JSON.stringify(v) : v)) }
  },
  'voice/Latency': async () => ({
    rows: [],
    note: 'a latência medida do kernel fica no trilho à direita, em LATENCY',
  }),
  'voice/Radio': async () => {
    const [st, qu] = await Promise.all([
      api.radioStatus().catch(() => null),
      api.radioQueue().catch(() => ({ queue: [] })),
    ])
    const s = st?.state ?? {}
    const cur = s.current_track
    const rows = [
      row('Tocando', cur ? `${cur.title}${cur.artist ? ` — ${cur.artist}` : ''}` : 'nada'),
      row('Fila', s.queue_length ?? 0),
      row('Volume', s.volume != null ? `${Math.round(s.volume * 100)}%` : '—'),
      row('Shuffle', s.shuffle ? 'ligado' : 'desligado'),
      row('Repeat', s.repeat ? 'ligado' : 'desligado'),
      row('Adblock', s.ad_blocker_enabled ? 'ligado' : 'desligado'),
      ...(qu.queue ?? []).slice(0, 6).map((t) => row(t.title, `${t.artist ?? ''} · ${t.stream_type ?? ''}`)),
    ]
    return {
      rows,
      note: 'tocar: paleta `tocar <busca>` · volume: `volume <0-100>` · `pular faixa` · `tocar preset <n>`',
    }
  },

  // ── Network ────────────────────────────────────────────────
  'network/Nodes': async () => {
    const h = await api.health()
    return {
      rows: [
        row('Kernel', `${h.app} ${h.version}`),
        row('Access mode', h.access_mode),
        row('Origem', location.host),
        row('Brain online', h.brain_online ? 'sim' : 'não'),
      ],
    }
  },
  'network/Traffic': async () =>
    absent('o kernel não contabiliza tráfego de rede. O que ele mede está em System.'),
  'network/Devices': async () => {
    const ds = await api.devices()
    return listing(
      ds,
      (d) => row(d.name ?? d.id, `${d.platform ?? ''} · ${d.revoked ? 'revogado' : 'ativo'}`),
      'nenhum aparelho pareado',
    )
  },
  'network/Actions': async () => {
    const cmds = await api.actionsHistory()
    return listing(
      cmds,
      (c) => row(
        `${c.action}${Object.keys(c.params ?? {}).length ? ` ${JSON.stringify(c.params)}` : ''}`,
        `${c.device_id} · ${c.status}${c.error ? ` · erro: ${truncate(c.error, 60)}` : ''} · ${when(c.created_at)}`,
      ),
      'nenhum comando enviado aos aparelhos ainda',
    )
  },
  'network/VPN': async () =>
    absent('o kernel não gerencia VPN. Ele escuta em loopback ou na LAN — veja Access mode em Nodes.'),

  // ── System: the host, measured ─────────────────────────────
  'system/CPU': async () => {
    const s = await api.system()
    return {
      rows: [
        row('Uso', pct(s.cpu.percent)),
        row('Núcleos lógicos', s.cpu.cores_logical),
        row('Núcleos físicos', s.cpu.cores_physical),
        row('Host', `${s.host.system} ${s.host.release} · ${s.host.machine}`),
        row('Uptime', duration(s.uptime_seconds)),
      ],
    }
  },
  'system/Memory': async () => {
    const s = await api.system()
    return {
      rows: [
        row('Uso', pct(s.memory.percent)),
        row('Usada', bytes(s.memory.used_bytes)),
        row('Disponível', bytes(s.memory.available_bytes)),
        row('Total', bytes(s.memory.total_bytes)),
      ],
    }
  },
  'system/Disk': async () => {
    const s = await api.system()
    return {
      rows: [
        row('Uso', pct(s.disk.percent)),
        row('Usado', bytes(s.disk.used_bytes)),
        row('Livre', bytes(s.disk.free_bytes)),
        row('Total', bytes(s.disk.total_bytes)),
      ],
    }
  },
  'system/Power': async () => {
    const s = await api.system()
    if (!s.battery) return absent(s.unavailable?.battery ?? 'esta máquina não reporta bateria')
    return {
      rows: [
        row('Carga', pct(s.battery.percent)),
        row('Na tomada', s.battery.plugged ? 'sim' : 'não'),
        row('Restante', s.battery.seconds_left === null ? '—' : duration(s.battery.seconds_left)),
      ],
    }
  },
  'system/Temp': async () => {
    const s = await api.system()
    return absent(s.unavailable?.temperature ?? 'temperatura não é legível nesta plataforma')
  },
  'system/Time': async () => {
    const [sm, cur] = await Promise.all([
      api.timeSummary().catch(() => []),
      api.timeCurrent().catch(() => null),
    ])
    const seconds = (s) => {
      if (typeof s !== 'number' || !isFinite(s)) return '—'
      const h = Math.floor(s / 3600)
      const m = Math.floor((s % 3600) / 60)
      return h > 0 ? `${h}h ${m}m` : `${m}m`
    }
    const running = cur?.running
    return {
      rows: [
        row('Agora', running ? `${running.label} (desde ${when(running.started_at)})` : 'nenhum timer aberto'),
        ...sm.slice(0, 10).map((x) => row(x.label, seconds(x.seconds))),
      ],
      note: 'tempo fechado por rótulo — `iniciar timer <rótulo>` / `parar timer`',
    }
  },
  'system/Optimize': async () => {
    const o = await api.optimize()
    const host = o.host ?? {}
    const rows = [
      row('Ollama', o.endpoint),
      row('Máquina', `${host.cores ?? '?'} núcleos · ${host.ram_gb ?? '?'} GB RAM`),
      ...(o.models ?? []).map((m) =>
        row(m.name, `${m.size_gb ?? '?'} GB · ${m.quantization ?? '?'} · ${m.loaded ? 'na RAM' : 'em disco'}`),
      ),
    ]
    const findings = (o.findings ?? []).filter(Boolean)
    const actions = (o.actions ?? []).filter(Boolean)
    return {
      rows,
      note: [
        findings.length ? `achados: ${findings.join(' · ')}` : null,
        actions.length ? `ações: ${actions.join(' · ')}` : null,
        'medir a inferência real: paleta `medir otimização` (lento — minutos em CPU)',
      ].filter(Boolean).join(' — '),
    }
  },

  // ── Settings ───────────────────────────────────────────────
  'settings/Core': async () => {
    const h = await api.health()
    return { rows: Object.entries(h).map(([k, v]) => row(k, v)) }
  },
  'settings/Voice': async () => {
    const s = await api.voiceStatus()
    return { rows: Object.entries(s).map(([k, v]) => row(k, typeof v === 'object' ? JSON.stringify(v) : v)) }
  },
  'settings/Theme': async () => ({
    rows: [row('Tema', 'ARC — único'), row('Movimento', matchMedia('(prefers-reduced-motion: reduce)').matches ? 'reduzido (respeitando o sistema)' : 'completo')],
    note: 'o tema acompanha a preferência de movimento do sistema operacional',
  }),
  'settings/About': async () => {
    const h = await api.health()
    return {
      rows: [
        row('Sistema', h.app),
        row('Versão', h.version),
        row('Cérebro', h.brain_model),
        row('Modo de acesso', h.access_mode),
      ],
      note: 'roda inteiro na sua máquina; nada sai daqui',
    }
  },
}

/** The loader for a module/sub-item pair, or null when none is mapped. */
export function panelFor(moduleId, item) {
  return PANELS[`${moduleId}/${item}`] ?? null
}
