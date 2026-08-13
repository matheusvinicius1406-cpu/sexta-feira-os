import { useState, useCallback } from 'react'
import { useStore } from '../store'
import { listAutomations, runAutomation } from '../hooks/useKernel'
import { AnimatePresence, motion } from 'framer-motion'

/**
 * Automations panel — the Teia workflows: list, enable/disable, run.
 */
export function AutomationsPanel() {
  const activePanel = useStore((s) => s.activePanel)
  const pushDataStream = useStore((s) => s.pushDataStream)
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listAutomations()
      setItems(data)
      pushDataStream('AUTOMATIONS', `${data.length} automação(ões)`)
    } catch (e: any) {
      setError(e.message?.includes('fetch') ? 'Kernel offline' : e.message)
    } finally {
      setLoading(false)
    }
  }, [pushDataStream])

  const run = useCallback(async (slug: string) => {
    setRunning(slug)
    try {
      const result = await runAutomation(slug)
      pushDataStream('AUTOMATIONS', `${slug}: ${result?.status ?? 'ok'}`)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setRunning(null)
    }
  }, [pushDataStream])

  if (activePanel !== 'automations') return null

  return (
    <AnimatePresence>
      <motion.div
        className="panel-overlay"
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      >
        <div className="panel-header">
          <span>⚙️ Automações (Teia)</span>
          <button className="panel-refresh" onClick={refresh} disabled={loading}>
            {loading ? '…' : '↻'}
          </button>
        </div>

        {error && <div className="security-error">⚠️ {error}</div>}

        {items.length === 0 && !loading && !error && (
          <button className="security-load" onClick={refresh}>Carregar automações</button>
        )}

        {items.map((a) => (
          <div key={a.slug} className="automation-item">
            <div className="automation-info">
              <div className="automation-name">{a.name ?? a.slug}</div>
              <div className="automation-desc">{a.description ?? a.slug}</div>
            </div>
            <div className="automation-actions">
              <span className={`automation-badge ${a.enabled ? 'on' : 'off'}`}>
                {a.enabled ? 'ativa' : 'off'}
              </span>
              <button
                className="automation-run"
                onClick={() => run(a.slug)}
                disabled={running === a.slug}
              >
                {running === a.slug ? '…' : '▶'}
              </button>
            </div>
          </div>
        ))}
      </motion.div>
    </AnimatePresence>
  )
}
