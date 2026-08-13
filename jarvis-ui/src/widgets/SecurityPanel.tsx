import { useState, useCallback } from 'react'
import { useStore } from '../store'
import { securityAudit, securityThreats } from '../hooks/useKernel'
import { AnimatePresence, motion } from 'framer-motion'

/**
 * Security dashboard — reads the kernel's posture report (/security/audit)
 * and the threat trail (/security/threats). All owner-only endpoints.
 */
export function SecurityPanel() {
  const activePanel = useStore((s) => s.activePanel)
  const pushDataStream = useStore((s) => s.pushDataStream)
  const [audit, setAudit] = useState<any>(null)
  const [threats, setThreats] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [a, t] = await Promise.all([securityAudit(), securityThreats()])
      setAudit(a)
      setThreats(t)
      pushDataStream('SECURITY', `${a?.ameacas?.total ?? 0} ameaça(s) registrada(s)`)
    } catch (e: any) {
      setError(e.message?.includes('fetch') ? 'Kernel offline' : e.message)
    } finally {
      setLoading(false)
    }
  }, [pushDataStream])

  if (activePanel !== 'security') return null

  const defesas = audit?.defesas ?? {}
  const ameacas = audit?.ameacas ?? { total: 0, recentes: [] }
  const bypass = audit?.acesso?.authDevBypass === true

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
          <span>🛡️ Segurança — Defesa Ativa</span>
          <button className="panel-refresh" onClick={refresh} disabled={loading}>
            {loading ? '…' : '↻'}
          </button>
        </div>

        {error && <div className="security-error">⚠️ {error}</div>}

        {!audit && !loading && !error && (
          <button className="security-load" onClick={refresh}>Auditar o kernel agora</button>
        )}

        {audit && (
          <div className="security-body">
            <div className="security-status">
              <span>Acesso: <b>{audit?.acesso?.accessMode ?? '?'}</b></span>
              {bypass && <span className="security-bad">⚠️ AUTH_DEV_BYPASS LIGADO — desligue no .env</span>}
            </div>
            <div className="security-grid">
              <div className="security-card">
                <b>{ameacas.total}</b>
                <span>ameaças detectadas</span>
              </div>
              <div className="security-card">
                <b>{defesas?.honeypotsArmed ?? 0}</b>
                <span>honeypots armados</span>
              </div>
              <div className="security-card">
                <b>{defesas?.netguard?.ativo ? 'ON' : 'OFF'}</b>
                <span>netguard (SSRF)</span>
              </div>
              <div className="security-card">
                <b>{defesas?.rateLimit?.maxTentativas ?? 5}</b>
                <span>tentativas até lockout</span>
              </div>
            </div>
            {(audit?.recomendacoes ?? []).length > 0 && (
              <div className="security-recs">
                {audit.recomendacoes.map((r: string, i: number) => (
                  <div key={i} className="security-recs-item">• {r}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {threats.length > 0 && (
          <div className="security-threats">
            <div className="security-threats-title">Tripwires disparados</div>
            {threats.slice(0, 8).map((t) => (
              <div key={t.id} className="security-threat">
                <span className="security-threat-type">{t.type}</span>
                <span className="security-threat-detail">{t.detail}</span>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
