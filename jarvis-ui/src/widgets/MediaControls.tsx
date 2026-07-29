import { useCallback, useEffect, useRef, useState } from 'react'
import { useMedia } from '../hooks/useMedia'
import { useAudioAnalyzer } from '../hooks/useAudioAnalyzer'
import { sendChatMessageStream, speakText, transcribeAudio } from '../hooks/useKernel'
import { useStore } from '../store'

/** Split text at sentence boundaries, returning [sentences[], remainder]. */
function splitSentences(text: string): { sentences: string[]; remainder: string } {
  if (!text) return { sentences: [], remainder: '' }
  const boundary = /(?<=[.!?])\s+|(?<=\n)\s*/g
  const parts = text.split(boundary)
  if (parts.length <= 1) return { sentences: [], remainder: text }
  return {
    sentences: parts.slice(0, -1).filter(Boolean),
    remainder: parts[parts.length - 1] ?? '',
  }
}

export function MediaControls() {
  const {
    isRecording,
    recordingDuration,
    startRecording,
    stopRecording,
    cameraActive,
    videoRef,
    toggleCamera,
  } = useMedia()
  const [voicePhase, setVoicePhase] = useState<'idle' | 'transcribing' | 'thinking' | 'speaking'>('idle')
  const addMessage = useStore((s) => s.addMessage)
  const setActivePanel = useStore((s) => s.setActivePanel)
  const setBrainActivity = useStore((s) => s.setBrainActivity)
  const setProcessing = useStore((s) => s.setProcessing)

  // Streaming chat state refs
  const replyAccumulator = useRef('')
  const assistantMsgId = useRef<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // TTS audio queue
  const audioQueue = useRef<string[]>([])           // blob URLs queued for playback
  const isPlayingQueue = useRef(false)

  // Sentence buffer for progressive TTS
  const sentenceBuffer = useRef('')

  // Stop flag for streaming
  const streamStopped = useRef(false)

  // Audio analyzer for brain waveform visualization
  const analyzer = useAudioAnalyzer()

  // Cleanup audio + abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
      audioQueue.current.forEach((url) => URL.revokeObjectURL(url))
      audioQueue.current = []
    }
  }, [])

  // Helper: play the next audio in the queue
  const playNextInQueue = useCallback(() => {
    if (isPlayingQueue.current || audioQueue.current.length === 0) return
    isPlayingQueue.current = true

    const url = audioQueue.current.shift()!
    const audio = new Audio(url)

    // Connect audio to visual analyzer for brain waveform
    analyzer.connect(audio)

    audio.onended = () => {
      URL.revokeObjectURL(url)
      analyzer.disconnect()
      isPlayingQueue.current = false
      // If more in queue, keep playing
      if (audioQueue.current.length > 0) {
        playNextInQueue()
      } else if (voicePhase === 'speaking' && !abortRef.current) {
        // Stream is fully done and queue is empty
        setVoicePhase('idle')
        setBrainActivity(0.3 + Math.random() * 0.2)
      }
    }
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      analyzer.disconnect()
      isPlayingQueue.current = false
      if (audioQueue.current.length > 0) playNextInQueue()
    }
    audio.play().catch(() => {
      URL.revokeObjectURL(url)
      analyzer.disconnect()
      isPlayingQueue.current = false
      if (audioQueue.current.length > 0) playNextInQueue()
    })
  }, [voicePhase, analyzer])

  // Helper: send a completed sentence to TTS and queue it
  const speakSentence = useCallback(async (sentence: string) => {
    if (!sentence.trim()) return
    try {
      // Check TTL: don't speak if streaming was cancelled
      if (streamStopped.current) return

      const audioBlob = await speakText(sentence)
      const url = URL.createObjectURL(audioBlob)
      audioQueue.current.push(url)

      // Start playback if nothing is playing
      if (!isPlayingQueue.current) {
        playNextInQueue()
      }
    } catch {
      // TTS unavailable for this sentence — skip, text is already in chat
    }
  }, [playNextInQueue])

  // Helper: replace or update the assistant message in the chat
  const updateAssistantMessage = useCallback((content: string) => {
    const msgs = useStore.getState().messages
    if (assistantMsgId.current) {
      const idx = msgs.findIndex((m) => m.id === assistantMsgId.current)
      if (idx >= 0) {
        const updated = [...msgs]
        updated[idx] = { ...updated[idx], content }
        useStore.setState({ messages: updated })
        return
      }
    }
    // No existing assistant message — create one
    const id = crypto.randomUUID()
    assistantMsgId.current = id
    useStore.setState({
      messages: [...msgs, { role: 'assistant' as const, content, id }],
    })
  }, [])

  // Helper: replace the voice placeholder in store
  const replaceLastPlaceholder = useCallback((newContent: string) => {
    const msgs = useStore.getState().messages
    let idx = -1
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].content.startsWith('🎤 Grava')) { idx = i; break }
    }
    if (idx >= 0) {
      const updated = [...msgs]
      updated[idx] = { ...updated[idx], content: newContent }
      useStore.setState({ messages: updated })
    } else {
      addMessage({ role: 'user', content: newContent })
    }
  }, [addMessage])

  const isVoiceBusy = voicePhase !== 'idle'

  const handleMicClick = useCallback(async () => {
    if (isRecording) {
      setVoicePhase('transcribing')
      const blob = await stopRecording()
      let ttsStarted = false
      streamStopped.current = false

      if (blob && blob.size > 100) {
        // Add placeholder and immediately start replacing
        const placeholderId = crypto.randomUUID()
        const msgs = useStore.getState().messages
        useStore.setState({
          messages: [...msgs, { role: 'user', content: '🎤 Gravando áudio...', id: placeholderId }],
        })
        setActivePanel('chat')
        setBrainActivity(0.7 + Math.random() * 0.2)

        try {
          // Step 1: Transcribe audio
          const text = await transcribeAudio(blob)
          replaceLastPlaceholder(`🎤 ${text}`)
          setBrainActivity(0.5 + Math.random() * 0.2)

          // Step 2: Stream chat response + progressive TTS
          setVoicePhase('thinking')
          setProcessing(true)
          setBrainActivity(0.8)
          replyAccumulator.current = ''
          assistantMsgId.current = null
          sentenceBuffer.current = ''
          ttsStarted = true

          abortRef.current = new AbortController()
          const stream = sendChatMessageStream(text, abortRef.current.signal)

          for await (const event of stream) {
            if (streamStopped.current) break

            if (event.type === 'conversation_id') {
              useStore.getState().pushDataStream('VOICE', 'Stream iniciado')
            } else if (event.type === 'chunk') {
              replyAccumulator.current += event.data

              // Update chat message progressively
              updateAssistantMessage(replyAccumulator.current)

              // Buffer sentences for TTS
              sentenceBuffer.current += event.data
              // Don't hold more than 3 chars — process sentences as they form
              if (sentenceBuffer.current.length > 3) {
                const { sentences, remainder } = splitSentences(sentenceBuffer.current)
                if (sentences.length > 0) {
                  setVoicePhase('speaking')
                  sentenceBuffer.current = remainder
                  for (const sentence of sentences) {
                    speakSentence(sentence)
                  }
                }
              }
            } else if (event.type === 'done') {
              // Flush remaining sentence buffer
              if (sentenceBuffer.current.trim().length > 0) {
                speakSentence(sentenceBuffer.current.trim())
                sentenceBuffer.current = ''
              }
              useStore.getState().pushDataStream('VOICE', 'Chat completo via voz')
              setBrainActivity(0.6 + Math.random() * 0.2)

              // If queue is already empty, go to idle
              if (audioQueue.current.length === 0 && !isPlayingQueue.current) {
                setVoicePhase('idle')
              } else {
                setVoicePhase('speaking')
              }
            } else if (event.type === 'error') {
              updateAssistantMessage(`⚠️ ${event.data}`)
              break
            }
          }
        } catch (e: any) {
          if (!streamStopped.current) {
            const errMsg = e.message?.includes('fetch') ? 'Kernel offline' : e.message
            const currentMsgs = useStore.getState().messages
            const stillHasPlaceholder = currentMsgs.some((m) => m.content.startsWith('🎤 Grava'))
            if (stillHasPlaceholder) {
              replaceLastPlaceholder(`⚠️ ${errMsg}`)
            } else {
              addMessage({ role: 'assistant', content: `⚠️ ${errMsg}` })
            }
          }
        } finally {
          setProcessing(false)
        }
      }
      if (!ttsStarted) setVoicePhase('idle')
    } else {
      await startRecording()
    }
  }, [isRecording, startRecording, stopRecording, addMessage, setActivePanel, setBrainActivity, setProcessing, replaceLastPlaceholder, updateAssistantMessage, speakSentence])

  // Stop speaking / streaming handler (for the stop button)
  const stopSpeaking = useCallback(() => {
    streamStopped.current = true

    // Abort the fetch request mid-stream
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }

    // Disconnect analyzer
    analyzer.disconnect()

    // Stop current audio
    audioQueue.current.forEach((url) => URL.revokeObjectURL(url))
    audioQueue.current = []
    isPlayingQueue.current = false
    setVoicePhase('idle')
    setBrainActivity(0.3)
  }, [analyzer])

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const micIcon = isVoiceBusy ? (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" className="mic-spinner">
      <path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z">
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 12 12"
          to="360 12 12"
          dur="1s"
          repeatCount="indefinite"
        />
      </path>
    </svg>
  ) : isRecording ? (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/>
    </svg>
  )

  const btnClass = [
    'media-btn',
    isRecording ? 'recording' : '',
    isVoiceBusy ? 'transcribing' : '',
  ]
    .filter(Boolean)
    .join(' ')

  const btnTitle = isVoiceBusy
    ? voicePhase === 'transcribing'
      ? 'Transcrevendo...'
      : voicePhase === 'thinking'
        ? 'Jarvis pensando...'
        : '🔊 Falando...'
    : isRecording
      ? `Parar gravação (${formatDuration(recordingDuration)})`
      : 'Gravar áudio'

  return (
    <>
      {/* Recording progress banner */}
      {isRecording && (
        <div className="recording-banner">
          <div className="recording-dot" />
          <span className="recording-text">
            Gravando {formatDuration(recordingDuration)}
          </span>
        </div>
      )}

      {/* Voice processing banner (transcribing / thinking / speaking) */}
      {isVoiceBusy && (
        <div className={`recording-banner ${voicePhase === 'speaking' ? 'speaking' : 'transcribing'}`}>
          <div className={`recording-dot ${voicePhase === 'speaking' ? 'speaking-dot' : 'transcribing-dot'}`} />
          <span className="recording-text">
            {voicePhase === 'transcribing' && 'Transcrevendo áudio...'}
            {voicePhase === 'thinking' && '🧠 Jarvis está pensando...'}
            {voicePhase === 'speaking' && '🔊 Jarvis está falando...'}
          </span>
          {/* Stop speaking / streaming button */}
          {voicePhase === 'speaking' && (
            <button
              className="speaking-stop"
              onClick={stopSpeaking}
              title="Parar"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Media buttons */}
      <div className="media-controls">
        <button
          className={btnClass}
          onClick={handleMicClick}
          disabled={isVoiceBusy}
          title={btnTitle}
        >
          {micIcon}
        </button>

        <button
          className={`media-btn ${cameraActive ? 'active' : ''}`}
          onClick={toggleCamera}
          disabled={isRecording || isVoiceBusy}
          title={cameraActive ? 'Desligar câmera' : 'Ligar câmera'}
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            {cameraActive ? (
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
            ) : (
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM15 16H5V8h10v8zm-2-2h-2v-2H9v-2h2V8h2v2h2v2h-2v2z"/>
            )}
          </svg>
        </button>
      </div>

      {/* Camera preview overlay */}
      {cameraActive && (
        <div className="camera-preview">
          <video
            ref={videoRef as React.RefObject<HTMLVideoElement>}
            autoPlay
            playsInline
            muted
            className="camera-video"
          />
        </div>
      )}
    </>
  )
}
