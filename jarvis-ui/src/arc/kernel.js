/**
 * The link to the kernel.
 *
 * The ARC mockup invented its own activity — canned replies, staged link drops,
 * a random core load. None of that ships. This module is the single place the
 * HUD gets a real reading from, and every readout it feeds is measured, not
 * generated: if a number cannot be sourced, it reads `—` rather than a
 * plausible-looking lie. An instrument that invents values is worse than one
 * that admits it has none.
 *
 * Talks to the kernel through the Vite dev proxy (`/api` → 127.0.0.1:8000), so
 * the browser never makes a cross-origin request.
 */

const API = '/api/v1'
const POLL_MS = 2000
const TIMEOUT_MS = 4000

/** What the HUD is allowed to display. Everything here was measured. */
export const snapshot = {
  connected: false,
  brainOnline: false,
  version: '',
  model: '',
  accessMode: '',
  /** Round-trip to /health, in ms. null while unknown. */
  latencyMs: null,
  /** Consecutive failed polls — drives offline vs. error. */
  failures: 0,
}

/** Reactor state derived from what the kernel actually reports. */
export function reactorState() {
  if (!snapshot.connected) return snapshot.failures > 3 ? 'error' : 'offline'
  if (!snapshot.brainOnline) return 'warning'
  return 'idle'
}

/** The LINK readout: where we are actually talking to, or that we are not. */
export function linkLabel() {
  if (!snapshot.connected) return 'LINK SEVERED'
  const host = location.host || '127.0.0.1:8000'
  return `HTTP · ${host}`
}

async function poll() {
  const started = performance.now()
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(`${API}/health`, { signal: controller.signal, cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()

    snapshot.latencyMs = Math.round(performance.now() - started)
    snapshot.connected = true
    snapshot.failures = 0
    snapshot.brainOnline = data.brain_online ?? false
    snapshot.version = data.version ?? ''
    snapshot.model = data.brain_model ?? ''
    snapshot.accessMode = data.access_mode ?? ''
  } catch {
    snapshot.connected = false
    snapshot.brainOnline = false
    snapshot.latencyMs = null
    snapshot.failures += 1
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Start polling. `onState` fires only when the derived state actually changes,
 * so the reactor is never told to re-enter the state it is already in.
 */
export function start(onState) {
  let last = null
  const tick = async () => {
    await poll()
    const next = reactorState()
    if (next !== last) {
      last = next
      onState?.(next, snapshot)
    }
  }
  tick()
  setInterval(tick, POLL_MS)
}
