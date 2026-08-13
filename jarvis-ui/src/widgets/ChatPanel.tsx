import { useState, useRef, useEffect, useCallback } from 'react'
import { useStore } from '../store'
import { sendChatMessage, voiceChat } from '../hooks/useKernel'
import { AnimatePresence, motion } from 'framer-motion'

/**
 * Records microphone audio (webm/opus) and returns the blob.
 */
async function recordAudio(): Promise<Blob> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  return new Promise<Blob>((resolve, reject) => {
    const chunks: Blob[] = []
    // Prefer ogg/opus (suportado pelo faster-whisper do kernel); fallback webm.
    const mime = MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
      ? 'audio/ogg;codecs=opus'
      : 'audio/webm;codecs=opus'
    let recorder: MediaRecorder | null = null
    try {
      recorder = new MediaRecorder(stream, { mimeType: mime })
    } catch {
      recorder = new MediaRecorder(stream)
    }
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      resolve(new Blob(chunks, { type: mime }))
    }
    recorder.onerror = (e: any) => {
      stream.getTracks().forEach((t) => t.stop())
      reject(e.error ?? new Error('Falha ao gravar'))
    }
    recorder.start()
    // Guarda o recorder para o stop (fechamento por closure).
    ;(window as any).__jarvisRecorder = recorder
  })
}

export function ChatPanel() {
  const { activePanel, messages, addMessage, isProcessing, setProcessing } = useStore()
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const listRef = useRef<HTMLDivElement>(null!)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const send = async () => {
    if (!input.trim() || isProcessing) return
    const text = input.trim()
    setInput('')
    addMessage({ role: 'user', content: text })
    setProcessing(true)

    try {
      const reply = await sendChatMessage(text)
      addMessage({ role: 'assistant', content: reply })
      useStore.getState().setBrainActivity(0.6 + Math.random() * 0.3)
      setTimeout(() => useStore.getState().setBrainActivity(0.2 + Math.random() * 0.2), 2000)
    } catch (e: any) {
      addMessage({ role: 'assistant', content: `⚠️ ${e.message?.includes('fetch') ? 'Kernel offline. Verifique se o servidor está rodando.' : e.message}` })
    }
    setProcessing(false)
  }

  /** Record -> full voice loop (hear, think, speak). */
  const sendVoice = useCallback(async () => {
    if (isRecording || isProcessing) return
    try {
      setIsRecording(true)
      const audio = await recordAudio()
      ;(window as any).__jarvisRecorder?.stop()
      setIsRecording(false)
      if (audio.size < 200) {
        addMessage({ role: 'assistant', content: '⚠️ Nada ouvido — fale algo e tente de novo.' })
        return
      }
      setProcessing(true)
      addMessage({ role: 'user', content: '🎤 (áudio enviado)' })
      const result = await voiceChat(audio, true)
      addMessage({ role: 'user', content: `🎤 ${result.transcript}` })
      addMessage({ role: 'assistant', content: result.reply })
      if (result.audioWavBase64) {
        const audioEl = new Audio('data:audio/wav;base64,' + result.audioWavBase64)
        audioEl.play().catch(() => {})
      }
      useStore.getState().setBrainActivity(0.6 + Math.random() * 0.3)
    } catch (e: any) {
      setIsRecording(false)
      addMessage({
        role: 'assistant',
        content: `⚠️ ${e.message?.includes('Permission') ? 'Permissão de microfone negada.' : e.message}`,
      })
    } finally {
      setProcessing(false)
    }
  }, [isRecording, isProcessing, addMessage, setProcessing])

  const toggleRecord = useCallback(() => {
    if (isRecording) {
      ;(window as any).__jarvisRecorder?.stop()
      setIsRecording(false)
    } else {
      sendVoice()
    }
  }, [isRecording, sendVoice])

  if (activePanel !== 'chat') return null

  return (
    <AnimatePresence>
      <motion.div
        className="panel-overlay"
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      >
        <div className="chat-messages" ref={listRef}>
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-msg ${msg.role}`}>
              {msg.content}
            </div>
          ))}
          {isProcessing && <div className="processing-indicator">▌ processando...</div>}
        </div>
        <div className="chat-input-row">
          <input
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Comando para o Jarvis..."
          />
          <button
            className={`chat-mic ${isRecording ? 'recording' : ''}`}
            onClick={toggleRecord}
            disabled={isProcessing}
            title={isRecording ? 'Parar gravação' : 'Falar com o Jarvis (voz)'}
          >
            {isRecording ? '⏹' : '🎤'}
          </button>
          <button className="chat-send" onClick={send} disabled={isProcessing}>
            ➤
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
