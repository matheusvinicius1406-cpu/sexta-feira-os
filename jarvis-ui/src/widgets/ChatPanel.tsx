import { useState, useRef, useEffect } from 'react'
import { useStore } from '../store'
import { sendChatMessage } from '../hooks/useKernel'
import { AnimatePresence, motion } from 'framer-motion'

export function ChatPanel() {
  const { activePanel, messages, addMessage, isProcessing, setProcessing } = useStore()
  const [input, setInput] = useState('')
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
          <button className="chat-send" onClick={send} disabled={isProcessing}>
            ➤
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
