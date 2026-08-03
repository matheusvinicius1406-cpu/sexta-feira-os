/**
 * The kernel's API, as the HUD sees it.
 *
 * `kernel.js` owns the heartbeat — the /health poll that drives the reactor.
 * This module owns everything else: the reads and writes behind the twelve
 * modules, plus chat, voice and vision.
 *
 * Three rules, all inherited from `kernel.js` and all load-bearing:
 *
 *   1. Nothing is invented. A panel shows what the kernel returned or it shows
 *      why it could not. There is no placeholder data anywhere in this file.
 *   2. A failure is reported as itself. 401 is not "empty", 503 is not "zero" —
 *      an owner staring at an empty list must be able to tell "nothing here"
 *      from "the kernel refused me".
 *   3. Every request has a deadline. A hung fetch would otherwise leave a panel
 *      on "loading" forever, which reads exactly like a broken feature.
 */

const API = '/api/v1'
const TIMEOUT_MS = 8000
/** Voice and vision hit the local model; a 8s deadline would cut off real work. */
const SLOW_TIMEOUT_MS = 120000

/** Raised for any non-2xx, carrying enough to explain itself on screen. */
export class KernelError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }

  /** What the panel shows. Distinguishes the cases an owner must tell apart. */
  get human() {
    if (this.status === 401) return 'kernel exigiu autenticação (AUTH_DEV_BYPASS está desligado?)'
    if (this.status === 403) return 'autenticado, mas sem permissão para isto'
    if (this.status === 404) return 'este kernel não expõe esse recurso'
    if (this.status === 503) return this.detail || 'recurso indisponível neste kernel'
    if (this.status === 0) return 'sem resposta do kernel'
    return this.detail || `kernel respondeu ${this.status}`
  }
}

async function request(path, { method = 'GET', body, timeout = TIMEOUT_MS, raw = false } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const init = { method, signal: controller.signal, cache: 'no-store' }
    if (body instanceof FormData) {
      init.body = body
    } else if (body !== undefined) {
      init.headers = { 'Content-Type': 'application/json' }
      init.body = JSON.stringify(body)
    }
    const res = await fetch(`${API}${path}`, init)
    if (!res.ok) {
      let detail = ''
      try {
        const err = await res.json()
        detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail ?? err)
      } catch {
        // A non-JSON error body is normal (proxy errors, HTML pages). The status
        // alone is still a real diagnosis, so do not let this hide it.
      }
      throw new KernelError(res.status, detail)
    }
    return raw ? res : await res.json()
  } catch (e) {
    if (e instanceof KernelError) throw e
    // AbortError and network failure both mean "no answer", which is a
    // different fact from any status the kernel could have returned.
    throw new KernelError(0, e.name === 'AbortError' ? `sem resposta em ${timeout} ms` : String(e.message || e))
  } finally {
    clearTimeout(timer)
  }
}

const get = (p, o) => request(p, o)
const post = (p, body, o) => request(p, { ...o, method: 'POST', body })

// ── System ───────────────────────────────────────────────────
export const system = () => get('/system')

// ── Brain / chat ─────────────────────────────────────────────
export const health = () => get('/health')
export const chat = (message, conversationId) =>
  post('/chat', { message, conversation_id: conversationId ?? null }, { timeout: SLOW_TIMEOUT_MS })
export const conversations = () => get('/chat/conversations')
export const conversation = (id) => get(`/chat/conversations/${encodeURIComponent(id)}`)

// ── Memory ───────────────────────────────────────────────────
export const memories = () => get('/memory')
export const recall = (query) => post('/memory/recall', { query }, { timeout: SLOW_TIMEOUT_MS })
export const memoryGraph = () => get('/memory/graph')
export const forget = (id) => request(`/memory/${encodeURIComponent(id)}`, { method: 'DELETE' })

// ── World (the present + the owner model) ────────────────────
export const world = () => get('/world')
export const worldProfile = () => get('/world/profile')
export const worldDigest = () => get('/world/digest')

// ── Events ───────────────────────────────────────────────────
export const events = () => get('/events')

// ── Agents: directors + the Teia ─────────────────────────────
export const directors = () => get('/directors')
export const automations = () => get('/automations')
export const automationStatus = () => get('/automations/status')
export const automationTypes = () => get('/automations/types')
export const executions = () => get('/automations/executions')
export const execution = (id) => get(`/automations/executions/${encodeURIComponent(id)}`)
export const runAutomation = (slug) =>
  post(`/automations/${encodeURIComponent(slug)}/run`, {}, { timeout: SLOW_TIMEOUT_MS })

// ── Files / vault ────────────────────────────────────────────
export const obsidianStatus = () => get('/obsidian/status')

// ── Projects: planning + briefing ────────────────────────────
export const goals = () => get('/planning/goals')
export const board = () => get('/planning/board')
export const briefingLatest = () => get('/briefing/latest')
export const briefings = () => get('/briefing')
export const generateBriefing = () => post('/briefing', {}, { timeout: SLOW_TIMEOUT_MS })

// ── Scheduling / jobs ────────────────────────────────────────
export const schedule = () => get('/schedule')

// ── Browser: the kernel's web reach ──────────────────────────
export const webSearch = (query) => post('/vision/search', { query }, { timeout: SLOW_TIMEOUT_MS })
export const searchAndFetch = (query) =>
  post('/vision/search_and_fetch', { query }, { timeout: SLOW_TIMEOUT_MS })

// ── Security ─────────────────────────────────────────────────
export const devices = () => get('/auth/devices')
export const secrets = () => get('/connectors/secrets')
export const connectors = () => get('/connectors')

// ── Voice ────────────────────────────────────────────────────
export const voiceStatus = () => get('/voice/status')
export const voicePacks = () => get('/voice/packs')
export const voicePersonality = () => get('/voice/personality')

/** Transcribe recorded audio. Returns `{ text }` — whatever the kernel heard. */
export async function transcribe(blob) {
  const form = new FormData()
  form.append('file', blob, 'fala.webm')
  return request('/voice/transcribe', { method: 'POST', body: form, timeout: SLOW_TIMEOUT_MS })
}

/**
 * The whole voice turn in one call: hear → think with memory → answer.
 *
 * Preferred over chaining transcribe + chat + speak from here. The kernel keeps
 * transcript, reply and audio consistent with each other and with the
 * conversation; three separate calls could half-succeed and leave the HUD
 * showing a reply to a question the kernel never recorded hearing.
 *
 * Returns `{ transcript, reply, conversation_id, audio_wav_base64 }` — the
 * audio is null when TTS is off or unavailable, and the text still stands.
 */
export async function voiceTurn(blob, { conversationId, speakReply = true } = {}) {
  const form = new FormData()
  form.append('file', blob, 'fala.webm')
  const params = new URLSearchParams()
  if (conversationId) params.set('conversation_id', conversationId)
  params.set('speak_reply', String(speakReply))
  const qs = params.toString()
  return request(`/voice/chat${qs ? `?${qs}` : ''}`, {
    method: 'POST', body: form, timeout: SLOW_TIMEOUT_MS,
  })
}

/** Synthesise speech. Returns an audio Blob ready for playback. */
export async function speak(text) {
  const res = await request('/voice/speak', {
    method: 'POST',
    body: { text },
    timeout: SLOW_TIMEOUT_MS,
    raw: true,
  })
  return res.blob()
}

// ── Vision ───────────────────────────────────────────────────
export const visionStatus = () => get('/vision/status')

/**
 * Describe a camera frame.
 *
 * The kernel's field is `frame_base64`, and its `_prepare_image` already strips
 * a `data:` prefix if one arrives — so passing a whole data URL works too. The
 * strip here is belt-and-braces at the boundary that produced the string, and
 * it keeps the payload smaller. It is not compensating for a kernel that
 * cannot cope.
 */
export const analyseFrame = (base64, question) =>
  post(
    '/vision/camera',
    { frame_base64: stripDataUrl(base64), question: question || undefined },
    { timeout: SLOW_TIMEOUT_MS },
  )

function stripDataUrl(s) {
  const comma = s.indexOf(',')
  return s.startsWith('data:') && comma !== -1 ? s.slice(comma + 1) : s
}

// ── Evals ────────────────────────────────────────────────────
export const evalCases = () => get('/evals/cases')
export const evalRuns = () => get('/evals/runs')

// ── Learning ─────────────────────────────────────────────────
export const learningStats = () => get('/learning/stats')
export const learnings = () => get('/learning')

// ── Journal / habits / time ──────────────────────────────────
export const journal = () => get('/journal')
export const habits = () => get('/habits')
export const timeSummary = () => get('/time/summary')
