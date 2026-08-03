/**
 * The live loop: chat, hearing, speech and sight.
 *
 * This is the part of the HUD that actually talks to the assistant. It owns the
 * conversation id, the microphone, the camera and the audio playback, and it
 * reports what it is doing through a single `onState` callback so the reactor
 * shows the real thing: `thinking` while the kernel is thinking, `speaking`
 * while audio is playing, `listening` while the microphone is open.
 *
 * Two commitments that shape the code:
 *
 *   * The reactor never claims an activity that is not happening. Previously it
 *     was moved by a timer; here every transition is bracketed around a real
 *     await, and `finally` returns it to idle even when the call throws.
 *   * Microphone and camera are released when not in use, and the camera has a
 *     visible on-screen preview whenever it is live. A silent capture device is
 *     a surveillance device.
 */
import * as api from './api.js'

const state = {
  conversationId: null,
  recorder: null,
  chunks: [],
  micStream: null,
  camStream: null,
  audio: null,
  busy: false,
}

let onState = () => {}
let onTranscript = () => {}
const el = {}

function init() {
  if (el.log) return
  el.chat = document.getElementById('chat')
  el.log = document.getElementById('chatLog')
  el.input = document.getElementById('chatInput')
  el.cam = document.getElementById('cam')
  el.camVideo = document.getElementById('camVideo')
  el.camCap = document.getElementById('camCap')
}

export function configure(handlers = {}) {
  init()
  onState = handlers.onState ?? onState
  onTranscript = handlers.onTranscript ?? onTranscript
}

// ── Chat surface ─────────────────────────────────────────────

function bubble(cls, text) {
  init()
  const d = document.createElement('div')
  d.className = `ch-msg ${cls}`
  d.textContent = text
  el.log.appendChild(d)
  el.log.scrollTop = el.log.scrollHeight
  return d
}

export function openChat() {
  init()
  el.chat.classList.add('on')
  setTimeout(() => el.input.focus(), 60)
}

export function closeChat() {
  init()
  el.chat.classList.remove('on')
  el.input.blur()
}

export function chatIsOpen() {
  init()
  return el.chat.classList.contains('on')
}

/** Send a typed message. Returns the reply text, or null when it failed. */
export async function say(text) {
  const message = String(text ?? '').trim()
  if (!message || state.busy) return null
  init()
  openChat()
  bubble('me', message)
  const waiting = bubble('wait', 'pensando…')
  state.busy = true
  onState('thinking')
  try {
    const res = await api.chat(message, state.conversationId)
    state.conversationId = res.conversation_id ?? state.conversationId
    waiting.remove()
    bubble('jv', res.reply)
    return res.reply
  } catch (e) {
    waiting.remove()
    bubble('err', e.human ?? String(e.message ?? e))
    return null
  } finally {
    state.busy = false
    onState('idle')
  }
}

// ── Speech out ───────────────────────────────────────────────

/** Play a WAV blob and hold `speaking` for exactly as long as it sounds. */
function play(blob) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    state.audio = audio
    const done = () => {
      URL.revokeObjectURL(url)
      state.audio = null
      resolve()
    }
    audio.onended = done
    // An audio element that fails to decode would otherwise leave the reactor
    // stuck on `speaking` with nothing coming out of the speakers.
    audio.onerror = done
    audio.play().catch(done)
  })
}

/** Speak a line through the kernel's TTS. */
export async function speak(text) {
  if (!text) return
  onState('speaking')
  try {
    await play(await api.speak(text))
  } catch (e) {
    bubble('err', `voz indisponível: ${e.human ?? e.message}`)
  } finally {
    onState('idle')
  }
}

// ── Hearing ──────────────────────────────────────────────────

function pickMime() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  return candidates.find((t) => window.MediaRecorder?.isTypeSupported?.(t)) ?? ''
}

/** Open the microphone and start recording. Idempotent. */
export async function startListening() {
  init()
  if (state.recorder || state.busy) return false
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    bubble('err', 'este navegador não expõe microfone (MediaRecorder ausente)')
    return false
  }
  try {
    state.micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (e) {
    // Denied permission is the owner's decision, not a fault — say which it is.
    bubble('err', `microfone não liberado: ${e.name === 'NotAllowedError' ? 'permissão negada' : e.message}`)
    return false
  }
  const mime = pickMime()
  state.chunks = []
  state.recorder = new MediaRecorder(state.micStream, mime ? { mimeType: mime } : undefined)
  state.recorder.ondataavailable = (e) => { if (e.data?.size) state.chunks.push(e.data) }
  state.recorder.start()
  onState('listening')
  onTranscript('ouvindo…')
  return true
}

function releaseMic() {
  state.micStream?.getTracks().forEach((t) => t.stop())
  state.micStream = null
  state.recorder = null
}

/**
 * Stop recording and run the full turn through the kernel: hear → think →
 * answer, spoken back when the kernel produced audio.
 */
export async function stopListeningAndSend() {
  if (!state.recorder) return null
  const recorder = state.recorder
  const blob = await new Promise((resolve) => {
    recorder.onstop = () => resolve(new Blob(state.chunks, { type: state.chunks[0]?.type || 'audio/webm' }))
    recorder.stop()
  })
  releaseMic()

  if (!blob.size) {
    onTranscript('')
    onState('idle')
    return null
  }

  openChat()
  state.busy = true
  onState('thinking')
  onTranscript('transcrevendo…')
  try {
    const res = await api.voiceTurn(blob, { conversationId: state.conversationId, speakReply: true })
    state.conversationId = res.conversation_id ?? state.conversationId
    onTranscript(res.transcript || '')
    if (res.transcript) bubble('me', res.transcript)
    bubble('jv', res.reply)

    if (res.audio_wav_base64) {
      state.busy = false
      onState('speaking')
      await play(b64ToBlob(res.audio_wav_base64, 'audio/wav'))
    }
    return res
  } catch (e) {
    bubble('err', e.human ?? String(e.message ?? e))
    return null
  } finally {
    state.busy = false
    onTranscript('')
    onState('idle')
  }
}

export function isListening() {
  return Boolean(state.recorder)
}

function b64ToBlob(b64, type) {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type })
}

// ── Sight ────────────────────────────────────────────────────

/** Turn the camera on, with the preview visible for as long as it is live. */
export async function startCamera() {
  init()
  if (state.camStream) return true
  if (!navigator.mediaDevices?.getUserMedia) {
    bubble('err', 'este navegador não expõe câmera')
    return false
  }
  try {
    state.camStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
    })
  } catch (e) {
    bubble('err', `câmera não liberada: ${e.name === 'NotAllowedError' ? 'permissão negada' : e.message}`)
    return false
  }
  el.camVideo.srcObject = state.camStream
  await el.camVideo.play().catch(() => {})
  el.cam.classList.add('on')
  return true
}

export function stopCamera() {
  init()
  state.camStream?.getTracks().forEach((t) => t.stop())
  state.camStream = null
  el.camVideo.srcObject = null
  el.cam.classList.remove('on')
}

export function cameraIsOn() {
  return Boolean(state.camStream)
}

/**
 * Grab a frame and ask the kernel what it sees.
 *
 * Turns the camera on if it is off, so "look" is one action rather than two,
 * and leaves it on afterwards — the preview stays visible, so the owner can
 * see that it is still running and turn it off deliberately.
 */
export async function look(question) {
  init()
  if (!(await startCamera())) return null
  const video = el.camVideo
  if (!video.videoWidth) {
    // The first frame has not arrived; capturing now yields a blank image and
    // the kernel would dutifully describe a black rectangle.
    await new Promise((r) => setTimeout(r, 350))
  }
  if (!video.videoWidth) {
    bubble('err', 'a câmera não entregou nenhum quadro')
    return null
  }

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  const frame = canvas.toDataURL('image/jpeg', 0.85)

  openChat()
  bubble('me', question ? `[câmera] ${question}` : '[câmera] o que você está vendo?')
  const waiting = bubble('wait', 'olhando…')
  state.busy = true
  onState('thinking')
  el.camCap.textContent = 'Analisando quadro'
  try {
    const res = await api.analyseFrame(frame, question)
    waiting.remove()
    const text = res.analysis ?? res.description ?? res.result ?? JSON.stringify(res)
    bubble('jv', text)
    return text
  } catch (e) {
    waiting.remove()
    bubble('err', e.human ?? String(e.message ?? e))
    return null
  } finally {
    state.busy = false
    el.camCap.textContent = 'Câmera ligada'
    onState('idle')
  }
}

/** Release every capture device. Called when the HUD is torn down. */
export function releaseAll() {
  releaseMic()
  stopCamera()
  state.audio?.pause()
}
