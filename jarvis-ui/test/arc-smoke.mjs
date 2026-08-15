/**
 * ARC smoke test — does the HUD actually run?
 *
 * `vite build` only proves the module PARSES. It says nothing about whether the
 * thing throws on the first frame, which is the difference between a working
 * HUD and a black screen. This harness gives the module a fake DOM and a fake
 * canvas, runs it through boot and a hundred frames at every depth, and fails
 * on the first exception.
 *
 * It deliberately does not assert on pixels — it asserts that the code path a
 * person actually takes (boot → open the core → pick a module → go back) never
 * throws. That is the regression this file exists to catch.
 *
 *   node test/arc-smoke.mjs
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')

// ── The ids the markup really provides ───────────────────────
const html = readFileSync(resolve(root, 'index.html'), 'utf8')
const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]))

const failures = []
let rafQueue = []
let now = 0

// ── Fakes ────────────────────────────────────────────────────

const gradient = () => ({ addColorStop() {} })

function fakeContext() {
  const noop = () => {}
  return new Proxy(
    {
      canvas: { width: 1920, height: 1080 },
      createLinearGradient: gradient,
      createRadialGradient: gradient,
      createConicGradient: gradient,
      measureText: () => ({ width: 40 }),
      getImageData: () => ({ data: new Uint8ClampedArray(4) }),
      setTransform: noop,
    },
    {
      get: (target, key) => (key in target ? target[key] : noop),
      set: () => true,
    },
  )
}

function element(id = '') {
  const el = {
    id,
    children: [],
    style: new Proxy({ setProperty() {} }, { get: (t, k) => t[k] ?? '', set: () => true }),
    dataset: {},
    classList: {
      _set: new Set(),
      add(c) { this._set.add(c) },
      remove(c) { this._set.delete(c) },
      toggle(c, on) { on ? this._set.add(c) : this._set.delete(c) },
      contains(c) { return this._set.has(c) },
    },
    textContent: '',
    innerHTML: '',
    getContext: () => fakeContext(),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1920, height: 1080 }),
    appendChild(child) { this.children.push(child); return child },
    removeChild(child) { this.children = this.children.filter((c) => c !== child) },
    addEventListener() {},
    removeEventListener() {},
    querySelectorAll: () => [],
    querySelector: () => null,
    focus() {},
    blur() {},
    remove() {},
    setAttribute() {},
    getAttribute: () => null,
    closest: () => null,
  }
  return el
}

const registry = new Map([...ids].map((id) => [id, element(id)]))

const listeners = new Map()

globalThis.document = {
  documentElement: element('html'),
  body: element('body'),
  getElementById(id) {
    if (!registry.has(id)) {
      // The exact bug this harness exists to catch: the script reaching for an
      // element the markup does not have. Record it, but keep going so one
      // miss does not hide the rest.
      failures.push(`document.getElementById("${id}") — id ausente no index.html`)
      registry.set(id, element(id))
    }
    return registry.get(id)
  },
  createElement: (tag) => element(`<${tag}>`),
  querySelector: () => element(),
  querySelectorAll: (sel) => (sel.includes('pip') ? [element(), element(), element()] : []),
  addEventListener(type, fn) { listeners.set(type, [...(listeners.get(type) ?? []), fn]) },
  removeEventListener() {},
  fonts: { ready: Promise.resolve() },
}

globalThis.window = globalThis
const _storage = new Map()
globalThis.localStorage = {
  getItem: (k) => (_storage.has(k) ? _storage.get(k) : null),
  setItem: (k, v) => _storage.set(k, String(v)),
  removeItem: (k) => _storage.delete(k),
}
globalThis.innerWidth = 1920
globalThis.innerHeight = 1080
globalThis.devicePixelRatio = 2
globalThis.location = { host: '127.0.0.1:3000', hash: '' }
globalThis.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} })
globalThis.addEventListener = (type, fn) =>
  listeners.set(type, [...(listeners.get(type) ?? []), fn])
globalThis.removeEventListener = () => {}
globalThis.requestAnimationFrame = (fn) => { rafQueue.push(fn); return rafQueue.length }
globalThis.cancelAnimationFrame = () => {}
globalThis.performance = { now: () => now }
globalThis.Path2D = class {
  rect() {} arc() {} moveTo() {} lineTo() {} closePath() {} bezierCurveTo() {}
  quadraticCurveTo() {} ellipse() {}
}
globalThis.CanvasRenderingContext2D = class {}
globalThis.CanvasRenderingContext2D.prototype.createConicGradient = function () {}

/**
 * A stand-in kernel that answers with the SHAPES the real one returns.
 *
 * A stub that answers `{}` to everything would let a loader reading
 * `list.slice(...)` pass here and throw the moment it met a real kernel — the
 * panel would render "falhou" and look like a backend problem. So each route
 * answers in the shape its router actually produces; anything not listed is a
 * 404, which is itself the answer for a route the HUD should not be calling.
 */
const HEALTH = {
  status: 'ok', app: 'Sexta-Feira OS', version: '1.0.0-kernel',
  brain_online: true, brain_model: 'qwen3-vl:2b', access_mode: 'loopback',
}
const GOAL = { id: 'g1', title: 'Meta', status: 'active', progress: 0.4, due_at: null }
const MEMO = { id: 'm1', title: 'Nota', content: 'conteúdo', kind: 'fact' }
const EVENT = { id: 'e1', type: 'kernel.ready', source: 'kernel', created_at: '2026-08-03T10:00:00Z' }

const ROUTES = {
  '/health': HEALTH,
  '/system': {
    cpu: { percent: 12.5, cores_logical: 8, cores_physical: 4 },
    memory: { total_bytes: 17e9, used_bytes: 8e9, available_bytes: 9e9, percent: 47.5 },
    disk: { total_bytes: 5e11, used_bytes: 2e11, free_bytes: 3e11, percent: 40 },
    battery: { percent: 29, plugged: false, seconds_left: 3220 },
    temperature: null,
    uptime_seconds: 98000,
    host: { system: 'Windows', release: '11', machine: 'AMD64', python: '3.14.6' },
    unavailable: { temperature: 'psutil não expõe sensor de temperatura em Windows' },
  },
  '/memory': [MEMO],
  '/memory/graph': { nodes: [{ id: 'n1', title: 'Nó', kind: 'fact' }], links: [] },
  '/world/digest': { digest: 'linha um\nlinha dois' },
  '/world': [], '/world/profile': [],
  '/events': [EVENT],
  '/directors': [{ name: 'engenharia', role: 'Engenharia', mandate: 'cuidar do código' }],
  '/agent/pulse': {
    enabled: true,
    last_report: { reason: 'heartbeat', noticed: [], executed: [], proposed: [], skipped: [] },
    pending_proposals: 1,
  },
  '/agent/proposals': [
    { id: 'p1', kind: 'acao', status: 'pending', title: 'Enviar lembrete', reason: 'o dono pediu', tool: 'notify', created_at: '2026-08-14T10:00:00Z' },
  ],
  '/automations': [{ slug: 'captura-rapida', enabled: true }],
  '/automations/status': { armed: 3, running: 0 },
  '/automations/types': { nodes: ['inicio', 'notificar'], triggers: ['agenda', 'evento'] },
  '/automations/executions': [{ id: 'x1', workflow_id: 'captura-rapida', status: 'sucesso', started_at: '2026-08-03T10:00:00Z' }],
  '/obsidian/status': { vault_path: 'C:/vault', default_path_configured: true, watching: false, note_count: 12 },
  '/planning/goals': [GOAL],
  '/planning/board': { pending: [GOAL], active: [], done: [] },
  '/briefing/latest': { id: 'b1', summary: 'Briefing\nFoco sugerido: Meta', created_at: '2026-08-03T07:00:00Z' },
  '/briefing': [],
  '/schedule': [{ id: 's1', kind: 'briefing', text: 'briefing diário', due_at: '2026-08-04T07:00:00Z', status: 'pending' }],
  '/auth/devices': [{ id: 'd1', name: 'celular', platform: 'android', revoked: false }],
  '/actions': [
    {
      id: 'c1', device_id: 'd1', action: 'abrir_app', params: { app: 'spotify' },
      status: 'done', result: 'ok', error: null, created_at: '2026-08-14T10:00:00Z',
    },
    {
      id: 'c2', device_id: 'd1', action: 'tocar_campainha', params: {},
      status: 'pending', result: null, error: null, created_at: '2026-08-14T11:00:00Z',
    },
  ],
  '/connectors/secrets': { names: ['OPENWEATHER', 'honeypot.api_falsa'] },
  '/security/audit': {
    auditado_em: '2026-08-14T10:00:00Z',
    acesso: { access_mode: 'loopback', auth_dev_bypass: false },
    defesas: {
      headers: ['X-Content-Type-Options', 'Content-Security-Policy'],
      rate_limit: { max_tentativas: 5, janela_segundos: 900, lockout_segundos: 900, ips_bloqueados_agora: 0 },
      netguard: { ativo: true, hosts_internos_permitidos: '' },
      honeypots_armados: 1,
    },
    ameacas: {
      total: 1,
      recentes: [{ id: 't1', type: 'threat.honeypot', detail: 'honeypot.api_falsa lido', source_ip: '127.0.0.1', at: '2026-08-14T09:00:00Z' }],
    },
    recomendacoes: [],
  },
  '/security/threats': [
    { id: 't1', type: 'threat.honeypot', detail: 'honeypot.api_falsa lido', source_ip: '127.0.0.1', at: '2026-08-14T09:00:00Z' },
  ],
  '/connectors': [
    {
      name: 'clima', description: 'tempo por cidade', category: 'general',
      method: 'GET', enabled: true, params: [{ name: 'cidade', required: true }],
    },
  ],
  '/radio/status': {
    enabled: true,
    state: {
      current_track: { id: 'radio-antena1', title: 'Antena 1', artist: '', stream_url: 'http://x', stream_type: 'internet_radio', duration: 0, thumbnail: '', has_ads: false, skip_segments: 0 },
      queue_length: 1,
      queue_index: 0,
      is_playing: true,
      volume: 0.8,
      shuffle: false,
      repeat: false,
      ad_blocker_enabled: true,
    },
  },
  '/radio/queue': {
    queue: [
      { id: 'radio-antena1', title: 'Antena 1', artist: '', stream_url: 'http://x', stream_type: 'internet_radio', duration: 0, thumbnail: '', has_ads: false, skip_segments: 0 },
    ],
    state: { queue_length: 1 },
  },
  '/radio/presets': [{ name: 'Antena 1', url: 'http://x' }],
  '/radio/stats': {
    state: { queue_length: 1, queue_index: 0, is_playing: true, volume: 0.8, shuffle: false, repeat: false, ad_blocker_enabled: true, current_track: null },
    ad_blocker: { sponsorblock_cache_size: 12, categories_blocked: ['music_offtopic'], ad_keywords_count: 40 },
    presets_count: 6,
  },
  '/radio/playlists': {
    playlists: [{ name: 'mix', count: 2, titles: ['Antena 1', 'Alpha'] }],
  },
  '/voice/status': {
    enabled: true, stt_available: true, tts_available: true, voicebox_enabled: true,
    voicebox_status: 'enabled', tts_engine: 'piper', voice_pack: 'Jarvis Classic',
  },
  '/voice/packs': [
    { name: 'Jarvis Classic', description: 'Tom profissional e direto.', key: 'jarvis', tts_voice: 'pt-BR-AntonioNeural', tts_rate: '-10%', tts_pitch: '-5Hz', voice_profile: 'borgerth-jarvis' },
    { name: 'Amigável', description: 'Tom casual e descontraído.', key: 'friendly', tts_voice: 'pt-BR-FranciscaNeural', tts_rate: '-5%', tts_pitch: '+2Hz', voice_profile: null },
    { name: 'Militar', description: 'Tom formal e direto.', key: 'military', tts_voice: 'pt-BR-AntonioNeural', tts_rate: '-20%', tts_pitch: '-10Hz', voice_profile: null },
    { name: 'Ultron', description: 'Voz de Márcio Dondi.', key: 'ultron', tts_voice: 'pt-BR-AntonioNeural', tts_rate: '-15%', tts_pitch: '-12Hz', voice_profile: 'dondi-ultron' },
    { name: 'Alfred', description: 'Voz de Pádua Moreira.', key: 'alfred', tts_voice: 'pt-BR-AntonioNeural', tts_rate: '-20%', tts_pitch: '-8Hz', voice_profile: 'padua-alfred' },
  ],
  '/voice/personality': { greeting: 'Às ordens.' },
  '/vision/status': { available: true, model: 'qwen3-vl:2b' },
  '/evals/cases': [], '/evals/runs': [],
  '/decision/history': [
    { id: 'd1', question: 'O que focar agora?', policy: 'urgencia', chosen_id: 'g1', chosen_label: 'Meta', rationale: 'mais urgente e mais próximo', options: [{ label: 'Meta' }], created_at: '2026-08-14T10:00:00Z' },
  ],
  '/network/traffic': {
    since_boot: { bytes_sent: 1500000000, bytes_recv: 8200000000, packets_sent: 900000, packets_recv: 1200000, errin: 0, errout: 0, dropin: 2, dropout: 5 },
    rate: { bytes_sent_per_s: 12345.6, bytes_recv_per_s: 98765.4, packets_sent_per_s: 12.5, packets_recv_per_s: 80.2, measured_over_s: 5.0 },
    interfaces: [
      { name: 'Ethernet', bytes_sent: 1500000000, bytes_recv: 8000000000, packets_sent: 900000, packets_recv: 1200000, errin: 0, errout: 0, dropin: 2, dropout: 5 },
      { name: 'Wi-Fi', bytes_sent: 50000000, bytes_recv: 200000000, packets_sent: 10000, packets_recv: 20000, errin: 0, errout: 0, dropin: 0, dropout: 0 },
    ],
    connections: { count: 42, by_state: { ESTABLISHED: 30, LISTEN: 8, TIME_WAIT: 4 } },
    unavailable: {},
  },
  '/network/vpn': {
    vpn_active: true,
    vpn_interfaces: [
      { name: 'utun4', up: true, addresses: ['10.8.0.2', 'fe80::abcd'] },
      { name: 'tun0', up: false, addresses: [] },
    ],
    default_route_interface: 'utun4',
    method: 'heuristic por nome de interface (o kernel mede; não conecta VPN)',
    unavailable: {},
  },
  '/browser/tabs': {
    tabs: [
      { query: 'otimização llama.cpp', kind: 'search', results: 5, top_url: null, at: '2026-08-15T10:00:00Z' },
      { query: 'qwen3 vision', kind: 'search_and_fetch', results: 3, top_url: 'https://huggingface.co/Qwen/Qwen3-VL', at: '2026-08-15T09:55:00Z' },
    ],
    count: 2,
    session_started_at: '2026-08-15T09:00:00Z',
  },
  '/browser/marks': {
    marks: [
      { id: 'bk1', title: 'Ollama', url: 'https://ollama.com', created_at: '2026-08-15T08:00:00Z' },
    ],
    count: 1,
  },
  '/terminal/ssh': {
    ssh_server: { listening: true, port: 22, process: 'sshd' },
    sessions: [
      { user: 'marcos', host: '192.168.1.20', terminal: 'pts/1', remote: true, started_at: '2026-08-15T10:00:00Z' },
      { user: 'marcos gas', host: null, terminal: null, remote: false, started_at: '2026-08-15T09:00:00Z' },
    ],
    sessions_count: 2,
    remote_count: 1,
    note: 'o kernel reporta sessões SSH; não abre shell, não faz proxy nem encaminha porta.',
    unavailable: {},
  },
  '/optimize': {
    endpoint: 'http://127.0.0.1:11434',
    host: { cores: 8, ram_gb: 16 },
    models: [
      { name: 'qwen3-vl:2b', size_gb: 1.9, quantization: 'Q4_K_M', capabilities: ['completion', 'tools', 'vision'], loaded: true },
    ],
    findings: ['Nada gritante: a configuração atual está coerente com esta máquina.'],
    actions: [],
  },
  '/learning': [], '/learning/stats': { total: 0, recent_avg_quality: null, recent_count: 0 },
  '/journal': [], '/habits': [],
  '/time/summary': [{ label: 'trabalho', seconds: 3600 }], '/time/current': { running: null },
  '/chat/conversations': [],
  '/cortex/verbs': {
    engine: 'symbolic',
    count: 17,
    verbs: [
      { name: 'tocar_playlist', description: 'tocar a playlist <nome>' },
      { name: 'tocar', description: 'tocar <música>' },
      { name: 'voz', description: 'trocar a voz' },
      { name: 'falar', description: 'o Jarvis fala um texto' },
      { name: 'hora', description: 'saber as horas' },
      { name: 'status', description: 'saber o estado do sistema' },
    ],
  },
  '/cortex/intent': {
    understood: true,
    verb: 'hora',
    target: null,
    params: {},
    trace: ['hora:padrão1'],
    response: 'São 14:32 de 15/08/2026.',
    raw: 'que horas são',
  },
  '/cortex/rules': {
    count: 2,
    regras: [
      {
        id: 'madrugada-silencio',
        descricao: 'De madrugada, com música tocando, sugere silêncio',
        prioridade: 30, auto: false,
        condicoes: { hora_entre: [23, 6], radio_tocando: true },
        acoes: [{ tipo: 'sugestao', valor: 'São horas de descanso, senhor.' }],
        arquivo: 'default.yaml',
      },
      {
        id: 'cpu-em-alta',
        descricao: 'CPU alta merece uma olhada',
        prioridade: 25, auto: false,
        condicoes: { cpu_maior_que: 90 },
        acoes: [{ tipo: 'observar', valor: 'CPU acima de 90%.' }],
        arquivo: 'default.yaml',
      },
    ],
  },
  '/cortex/rules/avaliar': {
    decisions: [
      {
        regra: 'madrugada-silencio',
        descricao: 'De madrugada, com música tocando, sugere silêncio',
        prioridade: 30, auto: false,
        acoes: [{ tipo: 'sugestao', valor: 'São horas de descanso, senhor.' }],
      },
    ],
    trail: [
      {
        regra: 'madrugada-silencio',
        descricao: 'De madrugada, com música tocando, sugere silêncio',
        disparou: true, auto: false,
        condicoes: [
          { condicao: 'hora_entre', esperado: [23, 6], passou: true, detalhe: 'hora=23 ∈ [23,6)' },
          { condicao: 'radio_tocando', esperado: true, passou: true, detalhe: 'radio_tocando=True (esperado True)' },
        ],
      },
    ],
    contexto: { agora: { hora: 23, dia_semana: 'sexta' }, radio: { tocando: true } },
  },
  '/cortex/decidir': {
    momento: '2026-08-15T23:00:00',
    decisao_id: 'dec-nucleo-1',
    contexto: { agora: { hora: 23, dia_semana: 'sexta' }, radio: { tocando: true } },
    regras: {
      total: 11, dispararam: 2,
      decisions: [{ regra: 'madrugada-silencio', descricao: 'De madrugada, com música tocando, sugere silêncio', prioridade: 30, auto: false, acoes: [{ tipo: 'sugestao', valor: 'São horas de descanso, senhor.' }] }],
      trail: [
        {
          regra: 'madrugada-silencio', descricao: 'De madrugada, com música tocando, sugere silêncio',
          disparou: true, auto: false,
          condicoes: [
            { condicao: 'hora_entre', esperado: [23, 6], passou: true, detalhe: 'hora=23 ∈ [23,6)' },
            { condicao: 'radio_tocando', esperado: true, passou: true, detalhe: 'radio_tocando=True (esperado True)' },
          ],
        },
      ],
    },
    foco: null,
    escolha: {
      tipo: 'regra', alvo: 'madrugada-silencio', descricao: 'De madrugada, com música tocando, sugere silêncio',
      acao: { tipo: 'sugestao', valor: 'São horas de descanso, senhor.' },
      rationale: "Regra 'madrugada-silencio' (prioridade 30) disparou contra o mundo atual — sinal forte do mundo vence o foco.",
      policy: 'regras_primeiro',
    },
  },
  '/cortex/decidir/ultimo': {
    decisao: {
      id: 'dec-nucleo-1', question: 'nucleo', policy: 'regras_primeiro',
      chosen_id: 'madrugada-silencio', chosen_label: 'De madrugada, com música tocando, sugere silêncio',
      rationale: "Regra 'madrugada-silencio' (prioridade 30) disparou contra o mundo atual — sinal forte do mundo vence o foco.",
      options: [{ tipo: 'regra', id: 'madrugada-silencio', prioridade: 30 }],
      created_at: '2026-08-15T23:00:00',
    },
  },
}

const seen = new Set()

globalThis.fetch = async (url) => {
  const path = String(url).replace(/^\/api\/v1/, '').replace(/\?.*$/, '')
  seen.add(path)
  if (!(path in ROUTES)) {
    return { ok: false, status: 404, json: async () => ({ detail: `sem rota ${path}` }) }
  }
  return { ok: true, status: 200, json: async () => ROUTES[path] }
}

// Timers fire immediately would recurse forever (boot chains setTimeout); keep
// them inert and drive the frames by hand instead.
const realSetTimeout = globalThis.setTimeout
globalThis.setTimeout = () => 0
globalThis.clearTimeout = () => {}
globalThis.setInterval = () => 0
globalThis.clearInterval = () => {}

// ── Run ──────────────────────────────────────────────────────

function pump(frames, label) {
  for (let i = 0; i < frames; i++) {
    const queued = rafQueue
    rafQueue = []
    now += 16.7
    for (const fn of queued) {
      try {
        fn(now)
      } catch (e) {
        failures.push(`${label}: frame lançou ${e && e.stack ? e.stack.split('\n')[0] : e}`)
        return
      }
    }
  }
}

function fire(type, event) {
  for (const fn of listeners.get(type) ?? []) {
    try {
      fn(event)
    } catch (e) {
      failures.push(`evento "${type}" lançou ${e && e.stack ? e.stack.split('\n')[0] : e}`)
    }
  }
}

await import('../src/arc/main.js')

pump(60, 'boot')

// Depth 0 → 1: the core opens the modules. This is the interaction the whole
// design is built around, so it is the one the test must actually take.
fire('keydown', { key: ' ', code: 'Space', preventDefault() {}, ctrlKey: false, metaKey: false })
pump(40, 'depth 1')

fire('pointermove', { clientX: 960 + 260, clientY: 540, preventDefault() {} })
pump(40, 'hover no setor anular')

fire('keydown', { key: 'ArrowRight', preventDefault() {}, ctrlKey: false, metaKey: false })
pump(20, 'setor com teclado')

fire('keydown', { key: 'Enter', preventDefault() {}, ctrlKey: false, metaKey: false })
pump(40, 'depth 2')

fire('keydown', { key: 'Escape', preventDefault() {}, ctrlKey: false, metaKey: false })
pump(40, 'volta')

fire('resize', {})
pump(20, 'resize')

// Let the kernel poll resolve so the telemetry path runs with real values.
await new Promise((r) => realSetTimeout(r, 50))
pump(20, 'pós-kernel')

// ── Every module sub-item must have a loader ─────────────────
//
// The twelve modules declare 51 sub-items between them. One without a loader is
// a menu entry that opens onto nothing — the exact "feature is simply absent"
// failure this project keeps finding. Read both lists from source and compare.

const modulesSrc = readFileSync(resolve(root, 'src/arc/modules.js'), 'utf8')
const moduleBlock = html.length && readFileSync(resolve(root, 'src/arc/main.js'), 'utf8')
const decl = moduleBlock.slice(moduleBlock.indexOf('const MODULES = ['))
const pairs = []
for (const line of decl.slice(0, decl.indexOf('];')).split('\n')) {
  if (!line.includes('kids:')) continue
  const id = line.match(/id:\s*"([^"]+)"/)[1]
  const kids = line.match(/kids:\s*\[([^\]]+)\]/)[1]
  for (const m of kids.matchAll(/"([^"]+)"/g)) pairs.push(`${id}/${m[1]}`)
}
const loaders = new Set([...modulesSrc.matchAll(/'([a-z]+\/[A-Za-z]+)':/g)].map((m) => m[1]))

for (const p of pairs) {
  if (!loaders.has(p)) failures.push(`submenu "${p}" não tem leitura mapeada em modules.js`)
}
for (const l of loaders) {
  if (!pairs.includes(l)) failures.push(`modules.js mapeia "${l}", que não existe em MODULES`)
}

// ── Every loader must survive a real answer ──────────────────
//
// Running them is the only way to know they parse the shapes the kernel sends.
// A loader doing `list.slice()` on an object throws a TypeError here rather
// than in front of the owner, where it would look like a backend fault.

const { PANELS } = await import('../src/arc/modules.js')
for (const [name, load] of Object.entries(PANELS)) {
  try {
    const out = await load()
    if (out.absent) {
      assert.equal(typeof out.absent, 'string', `${name}: 'absent' sem motivo`)
      continue
    }
    assert.ok(Array.isArray(out.rows), `${name}: não devolveu 'rows' nem 'absent'`)
    for (const r of out.rows) {
      assert.ok('k' in r && 'v' in r, `${name}: linha malformada ${JSON.stringify(r)}`)
      assert.equal(typeof r.v, 'string', `${name}: valor não é texto (${typeof r.v})`)
    }
  } catch (e) {
    // 404 from the stand-in kernel means this loader asked for a route the
    // kernel does not serve. Treating that as "a KernelError the panel will
    // render" would let every typo'd path pass here and fail silently in front
    // of the owner — the panel would say "este kernel não expõe esse recurso"
    // about a route that exists, misdirected by one wrong string.
    if (e && e.status === 404) {
      failures.push(`loader "${name}" chamou rota inexistente: ${e.detail || e.message}`)
      continue
    }
    if (e && e.constructor && e.constructor.name === 'KernelError') continue
    failures.push(`loader "${name}" lançou ${e && e.stack ? e.stack.split('\n')[0] : e}`)
  }
}

// ── Report ───────────────────────────────────────────────────

if (failures.length) {
  console.error(`\n✗ ARC smoke: ${failures.length} problema(s)\n`)
  for (const f of failures) console.error('  - ' + f)
  process.exit(1)
}

assert.ok(registry.get('reactor'), 'canvas do reator não foi tocado')
console.log(
  `✓ ARC smoke: boot, depth 0→1→2→0, hover, teclado, resize; ` +
  `${pairs.length} submenus com leitura; ${Object.keys(PANELS).length} loaders exercitados`,
)
