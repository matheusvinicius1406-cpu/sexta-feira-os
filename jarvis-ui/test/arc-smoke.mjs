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
  brain_online: true, brain_model: 'llava:7b', access_mode: 'loopback',
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
  '/automations': [{ slug: 'captura-rapida', enabled: true }],
  '/automations/status': { armed: 3, running: 0 },
  '/automations/types': { nodes: ['inicio', 'notificar'], triggers: ['agenda', 'evento'] },
  '/automations/executions': [{ id: 'x1', workflow_id: 'captura-rapida', status: 'sucesso', started_at: '2026-08-03T10:00:00Z' }],
  '/obsidian/status': { vault_path: 'C:/vault', default_path_configured: true, watching: false, note_count: 12 },
  '/planning/goals': [GOAL],
  '/planning/board': { pending: [GOAL], active: [], done: [] },
  '/briefing/latest': { id: 'b1', summary: 'Briefing\nFoco sugerido: Meta', created_at: '2026-08-03T07:00:00Z' },
  '/briefing': [],
  '/schedule': [{ id: 's1', name: 'briefing diário', action: 'briefing', next_run_at: '2026-08-04T07:00:00Z' }],
  '/auth/devices': [{ id: 'd1', name: 'celular', platform: 'android', revoked: false }],
  '/connectors/secrets': [{ name: 'OPENWEATHER' }],
  '/connectors': [],
  '/voice/status': { enabled: true, stt: 'whisper', tts: 'piper' },
  '/voice/packs': [{ name: 'jarvis', description: 'voz padrão' }],
  '/voice/personality': { greeting: 'Às ordens.' },
  '/vision/status': { available: true, model: 'llava:7b' },
  '/evals/cases': [], '/evals/runs': [],
  '/learning': [], '/learning/stats': { total: 0 },
  '/journal': [], '/habits': [], '/time/summary': {},
  '/chat/conversations': [],
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
