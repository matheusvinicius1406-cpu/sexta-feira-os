import { useStore } from '../store'
import { BrainActivityGraph } from './BrainActivityGraph'
import { DataStream } from './DataStream'
import { SystemMetrics } from './SystemMetrics'

function TopBar() {
  const { kernelStatus, uptime } = useStore()
  const hours = Math.floor(uptime / 3600)
  const mins = Math.floor((uptime % 3600) / 60)
  const memories = useStore((s) => s.memories)

  return (
    <div className="top-bar">
      <div className="system-title">
        <strong>JARVIS</strong> OS
        <div style={{ fontSize: 10, opacity: 0.4, marginTop: 4, letterSpacing: 2 }}>
          v{kernelStatus.version} · {kernelStatus.connected ? 'CONECTADO' : 'OFFLINE'}
        </div>
      </div>
      <div className="telemetry">
        <div className="telemetry-item">
          <span className="telemetry-label">Uptime</span>
          <span className="telemetry-value">{hours}h {mins}m</span>
        </div>
        <div className="telemetry-item">
          <span className="telemetry-label">Brain</span>
          <span className="telemetry-value" style={{ color: kernelStatus.brainOnline ? '#66ff88' : '#ff6644' }}>
            {kernelStatus.brainOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
        <div className="telemetry-item">
          <span className="telemetry-label">Nodes</span>
          <span className="telemetry-value">{memories.length}</span>
        </div>
      </div>
    </div>
  )
}

function Radar() {
  return (
    <div className="radar-container">
      <svg viewBox="0 0 80 80" className="radar-svg">
        <circle cx="40" cy="40" r="38" fill="none" stroke="rgba(68,136,255,0.15)" strokeWidth="0.5" />
        <circle cx="40" cy="40" r="25" fill="none" stroke="rgba(68,136,255,0.1)" strokeWidth="0.3" />
        <circle cx="40" cy="40" r="12" fill="none" stroke="rgba(68,136,255,0.08)" strokeWidth="0.3" />
        <line x1="40" y1="2" x2="40" y2="78" stroke="rgba(68,136,255,0.08)" strokeWidth="0.3" />
        <line x1="2" y1="40" x2="78" y2="40" stroke="rgba(68,136,255,0.08)" strokeWidth="0.3" />
        <line x1="8" y1="8" x2="72" y2="72" stroke="rgba(68,136,255,0.05)" strokeWidth="0.2" />
        <line x1="72" y1="8" x2="8" y2="72" stroke="rgba(68,136,255,0.05)" strokeWidth="0.2" />
        <polygon
          points="40,40 44,2 36,2"
          fill="rgba(68,136,255,0.06)"
          className="radar-sweep"
        />
        <circle cx="30" cy="25" r="1.5" fill="rgba(68,136,255,0.4)" />
        <circle cx="55" cy="35" r="1" fill="rgba(102,204,255,0.3)" />
        <circle cx="20" cy="50" r="0.8" fill="rgba(255,102,170,0.2)" />
      </svg>
    </div>
  )
}

export function HUD() {
  return (
    <div className="hud-overlay">
      <TopBar />
      <div style={{ position: 'fixed', top: 80, right: 30 }}>
        <BrainActivityGraph />
      </div>
      <DataStream />
      <SystemMetrics />
      <Radar />
    </div>
  )
}
