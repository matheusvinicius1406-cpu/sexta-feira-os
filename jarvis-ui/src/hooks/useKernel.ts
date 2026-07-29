import { useEffect, useRef } from 'react'
import { useStore } from '../store'

/**
 * Base path for all API calls.
 * Uses the Vite dev server proxy (/api → http://127.0.0.1:8000/api)
 * to avoid CORS issues from the browser.
 * In production, this would be the same path since the app is served
 * alongside the API or through a reverse proxy.
 */
const API_BASE = '/api/v1'

/**
 * Polls the kernel health endpoint every N seconds and updates the store.
 * Also fetches memories on auth and pushes data stream events.
 */
export function useKernel() {
  const setKernelStatus = useStore((s) => s.setKernelStatus)
  const pushBrainActivity = useStore((s) => s.pushBrainActivity)
  const pushDataStream = useStore((s) => s.pushDataStream)
  const setSystemMetrics = useStore((s) => s.setSystemMetrics)
  const intervalRef = useRef<ReturnType<typeof setInterval>|undefined>(undefined)
  const wasConnected = useRef(false)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 5000)
        const res = await fetch(`${API_BASE}/health`, { signal: controller.signal })
        clearTimeout(timeoutId)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const data = await res.json()
        const brainOnline = data.brain_online ?? data.brain_ok ?? false
        const version = data.version ?? data.app_version ?? '0.0.0'
        setKernelStatus({ connected: true, brainOnline, version })

        // Push brain activity based on real status
        const activity = brainOnline ? 0.5 + Math.random() * 0.3 : 0.1
        pushBrainActivity(activity)
        useStore.getState().setBrainActivity(activity)

        // Track connection state changes
        if (!wasConnected.current) {
          wasConnected.current = true
          pushDataStream('KERNEL', `v${version} ${brainOnline ? '🧠 online' : '🧠 offline'}`)
          pushDataStream('HEALTH', 'API conectada')
        }

        // Simulated metrics from real status
        setSystemMetrics({
          cpu: 15 + Math.random() * 20,
          memory: 25 + Math.random() * 15,
          sessions: 1,
          tokens: Math.floor(Math.random() * 100),
        })

        // Tick uptime
        useStore.getState().tickUptime()
      } catch {
        setKernelStatus({ connected: false, brainOnline: false, version: '0.0.0' })
        pushBrainActivity(0.1)
        useStore.getState().setBrainActivity(0.1)

        if (wasConnected.current) {
          wasConnected.current = false
          pushDataStream('KERNEL', '⚠️ Conexão perdida')
        }
      }
    }

    // Immediate first check
    checkHealth()

    // Then poll every 5s
    intervalRef.current = setInterval(checkHealth, 5000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [setKernelStatus, pushBrainActivity, pushDataStream, setSystemMetrics])
}

/**
 * Streams a chat message via SSE and yields chunks + conversation_id + done events.
 * POST /api/v1/chat/stream returns text/event-stream.
 * Pass an AbortSignal via `signal` to cancel mid-stream.
 */
export async function* sendChatMessageStream(
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<{
  type: 'chunk' | 'done' | 'conversation_id' | 'error'
  data: string
}> {
  const { token } = useStore.getState()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message }),
    signal,
  })

  if (!res.ok) {
    const errText = await res.text().catch(() => '')
    yield { type: 'error', data: `Chat error (${res.status}): ${errText.slice(0, 100)}` }
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    yield { type: 'error', data: 'Response body is not readable' }
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE lines: "data: {...}\\n\\n"
      const parts = buffer.split('\n')
      buffer = parts.pop() ?? ''  // keep incomplete line in buffer

      for (const line of parts) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(trimmed.slice(6))
            if ('conversation_id' in parsed) {
              yield { type: 'conversation_id', data: parsed.conversation_id }
            } else if ('chunk' in parsed) {
              yield { type: 'chunk', data: parsed.chunk }
            } else if ('done' in parsed) {
              yield { type: 'done', data: '' }
            } else if ('error' in parsed) {
              yield { type: 'error', data: parsed.error }
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * Sends a chat message to the kernel and returns the reply.
 */
export async function sendChatMessage(message: string): Promise<string> {
  const { token } = useStore.getState()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`Chat error: ${res.status}`)
  const data = await res.json()
  useStore.getState().pushDataStream('CHAT', 'Resposta recebida')
  return data.reply
}

/**
 * Fetches memory graph from the kernel.
 */
export async function fetchMemories(): Promise<{ id: string; title: string; kind: string; importance: number }[]> {
  const { token } = useStore.getState()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/memory`, { headers })
  if (!res.ok) throw new Error(`Memory error: ${res.status}`)
  const data = await res.json()

  // Normalize response (could be array or object with items/nodes)
  const nodes = Array.isArray(data) ? data : data.nodes ?? data.items ?? data.memories ?? []
  return nodes.map((n: any) => ({
    id: n.id ?? n.memory_id ?? '',
    title: n.title ?? n.content ?? n.name ?? 'sem título',
    kind: n.kind ?? n.type ?? 'fact',
    importance: n.importance ?? n.score ?? 0.5,
  }))
}

/**
 * Transcribes an audio blob using the kernel's STT endpoint.
 * POST /api/v1/voice/transcribe as multipart/form-data
 */
export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const { token } = useStore.getState()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const formData = new FormData()
  const filename = `recording_${Date.now()}.webm`
  formData.append('file', audioBlob, filename)

  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Transcribe error (${res.status}): ${text.slice(0, 100)}`)
  }
  const data = await res.json()
  useStore.getState().pushDataStream('STT', 'Áudio transcrito')
  return data.text ?? data.transcript ?? ''
}

/**
 * Synthesizes text to speech via the kernel's TTS endpoint.
 * POST /api/v1/voice/speak — returns raw WAV audio bytes.
 */
export async function speakText(text: string): Promise<Blob> {
  const { token } = useStore.getState()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/voice/speak`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ text }),
  })
  if (!res.ok) {
    const errText = await res.text().catch(() => '')
    throw new Error(`TTS error (${res.status}): ${errText.slice(0, 100)}`)
  }
  useStore.getState().pushDataStream('TTS', 'Fala sintetizada')
  return res.blob()
}

/**
 * Teaches the kernel a new fact.
 */
export async function teachMemory(content: string): Promise<void> {
  const { token } = useStore.getState()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/memory`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error(`Teach error: ${res.status}`)
  useStore.getState().pushDataStream('MEMORY', `Ensinado: "${content.slice(0, 30)}..."`)
}
