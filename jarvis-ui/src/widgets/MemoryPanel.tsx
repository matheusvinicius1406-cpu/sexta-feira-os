import { useEffect } from 'react'
import { useStore } from '../store'
import { fetchMemories as fetchKernelMemories } from '../hooks/useKernel'
import { AnimatePresence, motion } from 'framer-motion'

export function MemoryPanel() {
  const { activePanel, memories, setMemories } = useStore()

  useEffect(() => {
    if (activePanel === 'memory') {
      loadMemories()
    }
  }, [activePanel])

  const loadMemories = async () => {
    try {
      const nodes = await fetchKernelMemories()
      setMemories(nodes)
    } catch {}
  }

  if (activePanel !== 'memory') return null

  return (
    <AnimatePresence>
      <motion.div
        className="panel-overlay"
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      >
        <div style={{ fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', padding: '0 4px 8px' }}>
          Grafo de Memória · {memories.length} nós
        </div>
        <div className="memory-grid">
          {memories.slice(0, 30).map((m, i) => (
            <motion.div
              key={m.id}
              className="memory-chip"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
            >
              {m.title}
            </motion.div>
          ))}
          {memories.length === 0 && (
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)', padding: 20, textAlign: 'center' }}>
              Nenhuma memória encontrada
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
