import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[JARVIS UI] Runtime error:', error.message, error.stack)
    console.error('[JARVIS UI] Component stack:', info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{
          position: 'fixed', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#000811', color: '#4488ff',
          fontFamily: "'JetBrains Mono', monospace", flexDirection: 'column', gap: 16,
        }}>
          <div style={{ fontSize: 40 }}>⚠</div>
          <div style={{ fontSize: 14, letterSpacing: 2, textTransform: 'uppercase' }}>
            Runtime Error
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', maxWidth: 400, textAlign: 'center' }}>
            {this.state.error?.message || 'Unknown error'}
          </div>
          <button onClick={() => window.location.reload()} style={{
            marginTop: 8, padding: '8px 20px', borderRadius: 8,
            border: '1px solid rgba(68,136,255,0.3)', background: 'rgba(68,136,255,0.1)',
            color: '#4488ff', cursor: 'pointer', fontFamily: 'inherit', fontSize: 12,
          }}>
            RELOAD
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
