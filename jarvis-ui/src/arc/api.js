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
/**
 * Deadline for anything that reaches the local model.
 *
 * 120 s was too short and produced the worst possible outcome: the browser gave
 * up, showed "sem resposta do kernel", and the kernel went on to finish and
 * answer 200 into a closed socket. The owner was told the kernel was dead while
 * it was working. On a 4-core box a cold 4B turn takes ~150 s, so the
 * deadline now sits well past the slowest honest answer — it exists to catch a
 * kernel that is truly hung, not to race one that is merely thinking.
 */
const SLOW_TIMEOUT_MS = 600000

/** Raised for any non-2xx, carrying enough to explain itself on screen. */
export class KernelError extends Error {
  constructor(status, detail, { timedOut = false } = {}) {
    super(detail || `HTTP ${status}`)
    this.status = status
    this.detail = detail
    this.timedOut = timedOut
  }

  /** What the panel shows. Distinguishes the cases an owner must tell apart. */
  get human() {
    if (this.status === 401) return 'kernel exigiu autenticação (AUTH_DEV_BYPASS está desligado?)'
    if (this.status === 403) return 'autenticado, mas sem permissão para isto'
    if (this.status === 404) return 'este kernel não expõe esse recurso'
    if (this.status === 503) return this.detail || 'recurso indisponível neste kernel'
    // "Desisti de esperar" and "não há ninguém lá" send you to opposite places:
    // one is a slow model, the other is a kernel that is not running. Saying
    // "sem resposta do kernel" for both is how a working kernel gets blamed.
    if (this.timedOut) return this.detail || 'o kernel demorou demais e eu desisti de esperar'
    if (this.status === 0) return 'não consegui falar com o kernel — ele está rodando em 127.0.0.1:8000?'
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
    if (e.name === 'AbortError') {
      throw new KernelError(0, `o kernel passou de ${Math.round(timeout / 1000)}s sem responder`, {
        timedOut: true,
      })
    }
    throw new KernelError(0, String(e.message || e))
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
export const scheduleCreate = (body) => post('/schedule', body)
export const scheduleCancel = (id) =>
  request(`/schedule/${encodeURIComponent(id)}`, { method: 'DELETE' })

// ── Radio — mídia tocada pelo kernel ─────────────────────────
export const radioStatus = () => get('/radio/status')
export const radioQueue = () => get('/radio/queue')
export const radioPresets = () => get('/radio/presets')
export const radioSearch = (query) => post('/radio/search', { query }, { timeout: SLOW_TIMEOUT_MS })
export const radioPlay = (body) => post('/radio/play', body, { timeout: SLOW_TIMEOUT_MS })
export const radioSkip = () => post('/radio/skip', {})
export const radioVolume = (level) => post(`/radio/volume/${level}`, {})
export const radioPlayPreset = (index) => post(`/radio/presets/${index}`, {}, { timeout: SLOW_TIMEOUT_MS })
export const radioToggleShuffle = () => post('/radio/shuffle', {})
export const radioToggleRepeat = () => post('/radio/repeat', {})
export const radioToggleAdblock = () => post('/radio/adblock', {})

// ── Decision — por que o kernel escolheu o próximo objetivo ─
export const decisionHistory = () => get('/decision/history')
// Decide o foco agora (ranqueia metas abertas) — pode custar uma chamada ao cérebro.
export const decideNext = () => post('/decision/next', {}, { timeout: SLOW_TIMEOUT_MS })

// ── Optimizer — o kernel mede a própria inferência ───────────
export const optimize = () => get('/optimize')
// Probe: cronometra cada modelo (frio/quente, tok/s) — minutos em CPU.
export const optimizeProbe = () => post('/optimize/probe', {}, { timeout: SLOW_TIMEOUT_MS })
// Varredura completa: contexto, threads, batch, swap + linhas de .env.
export const optimizeFull = () => post('/optimize/full', {}, { timeout: SLOW_TIMEOUT_MS })

// ── Agent (Pulse) — a iniciativa própria do kernel ───────────
export const pulseStatus = () => get('/agent/pulse')
export const pulseRun = () => post('/agent/pulse/run', {}, { timeout: SLOW_TIMEOUT_MS })
export const proposals = (status) =>
  get(status ? `/agent/proposals?status=${encodeURIComponent(status)}` : '/agent/proposals')
export const approveProposal = (id) =>
  post(`/agent/proposals/${encodeURIComponent(id)}/approve`, {}, { timeout: SLOW_TIMEOUT_MS })
export const rejectProposal = (id) =>
  post(`/agent/proposals/${encodeURIComponent(id)}/reject`, {}, { timeout: SLOW_TIMEOUT_MS })

// ── Actions — as mãos do kernel em cada aparelho ─────────────
// Histórico de comandos enviados aos corpos (lado do dono).
export const actionsHistory = () => get('/actions')
// Envia um comando a um aparelho pareado (seletor: nome ou tipo natural).
export const actionDispatch = (device, action, params) =>
  post('/actions/dispatch', { device, action, params: params || {} })

// ── Security (defesa ativa) ──────────────────────────────────
export const securityAudit = () => get('/security/audit')
export const securityThreats = (limite = 30) => get(`/security/threats?limite=${limite}`)
export const setSecret = (name, value) => post('/connectors/secrets', { name, value })
export const deleteSecret = (name) =>
  request(`/connectors/secrets/${encodeURIComponent(name)}`, { method: 'DELETE' })

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
export const journalAdd = (content, mood) => post('/journal', { content, mood: mood ?? null })
export const habits = () => get('/habits')
export const habitCheck = (name) => post('/habits/check', { name })
export const timeSummary = () => get('/time/summary')
export const timeCurrent = () => get('/time/current')
export const timeStart = (label) => post('/time/start', { label })
export const timeStop = () => post('/time/stop', {})
