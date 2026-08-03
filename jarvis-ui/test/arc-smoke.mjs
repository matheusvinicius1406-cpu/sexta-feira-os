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

// The kernel is not running in a unit test — answer as if it were, so the
// telemetry path (which reads latency and version) is exercised for real.
globalThis.fetch = async () => ({
  ok: true,
  json: async () => ({
    status: 'ok',
    version: '1.0.0-kernel',
    brain_online: true,
    brain_model: 'llava:7b',
    access_mode: 'lan',
  }),
})

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

// ── Report ───────────────────────────────────────────────────

if (failures.length) {
  console.error(`\n✗ ARC smoke: ${failures.length} problema(s)\n`)
  for (const f of failures) console.error('  - ' + f)
  process.exit(1)
}

assert.ok(registry.get('reactor'), 'canvas do reator não foi tocado')
console.log('✓ ARC smoke: boot, depth 0→1→2→0, hover, teclado e resize sem exceção')
