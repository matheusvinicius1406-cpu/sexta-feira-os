import { useStore } from '../store'
import { HolographicPanel } from './HolographicPanel'

function MetricBar({ label, value, pct, color }: { label: string; value: string; pct: number; color: string }) {
  return (
    <div className="metric-row">
      <div className="metric-label">{label}</div>
      <div className="metric-bar-track">
        <div
          className="metric-bar-fill"
          style={{ width: `${pct * 100}%`, backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
        />
      </div>
      <div className="metric-value">{value}</div>
    </div>
  )
}

export function SystemMetrics() {
  const { systemMetrics, fps, uptime } = useStore()
  const hours = Math.floor(uptime / 3600)
  const mins = Math.floor((uptime % 3600) / 60)
  const cpuPct = Math.min(systemMetrics.cpu / 100, 1)
  const memPct = Math.min(systemMetrics.memory / 100, 1)

  return (
    <HolographicPanel title="SYSTEM METRICS" width={220} height={160} style={{ bottom: 110, right: 130, position: 'fixed' }}>
      <MetricBar
        label="CPU"
        value={`${systemMetrics.cpu.toFixed(1)}%`}
        pct={cpuPct}
        color={cpuPct > 0.7 ? '#ff6644' : '#4488ff'}
      />
      <MetricBar
        label="MEM"
        value={`${systemMetrics.memory.toFixed(1)}%`}
        pct={memPct}
        color={memPct > 0.7 ? '#ff6644' : '#66ccff'}
      />
      <div className="metric-row">
        <div className="metric-label">SESS</div>
        <div className="metric-value" style={{ flex: 1, textAlign: 'right' }}>{systemMetrics.sessions}</div>
      </div>
      <div className="metric-row">
        <div className="metric-label">FPS</div>
        <div className="metric-value" style={{ flex: 1, textAlign: 'right', color: fps < 30 ? '#ff6644' : '#66ff88' }}>{fps}</div>
      </div>
      <div className="metric-row">
        <div className="metric-label">UP</div>
        <div className="metric-value" style={{ flex: 1, textAlign: 'right' }}>{hours}h {mins}m</div>
      </div>
    </HolographicPanel>
  )
}
