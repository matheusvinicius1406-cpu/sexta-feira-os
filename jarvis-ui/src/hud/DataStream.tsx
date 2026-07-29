import { useStore } from '../store'
import { HolographicPanel } from './HolographicPanel'

export function DataStream() {
  const dataStream = useStore((s) => s.dataStream)

  return (
    <HolographicPanel title="DATA STREAM" width={280} height={160} style={{ bottom: 110, left: 30, position: 'fixed' }}>
      <div className="data-stream">
        {dataStream.length === 0 && (
          <div className="data-stream-empty">
            <span className="data-stream-time">--:--:--</span>
            <span className="data-stream-msg">Aguardando conexão...</span>
          </div>
        )}
        {dataStream.map((d, i) => (
          <div key={i} className="data-stream-item" style={{ animationDelay: `${i * 0.02}s` }}>
            <span className="data-stream-time">{d.time}</span>
            <span className="data-stream-label">{d.label}</span>
            <span className="data-stream-value">{d.value}</span>
          </div>
        ))}
      </div>
    </HolographicPanel>
  )
}
