import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useStore, storeHydrated } from './store'
import { useKernel } from './hooks/useKernel'
import { ErrorBoundary } from './components/ErrorBoundary'
import './styles/global.css'

// ── Lazy-loaded heavy components (code splitting) ──────
const Scene = lazy(() => import('./engine/Scene').then((m) => ({ default: m.Scene })))
const HUD = lazy(() => import('./hud/HUD').then((m) => ({ default: m.HUD })))
const ChatPanel = lazy(() => import('./widgets/ChatPanel').then((m) => ({ default: m.ChatPanel })))
const MemoryPanel = lazy(() => import('./widgets/MemoryPanel').then((m) => ({ default: m.MemoryPanel })))
const SecurityPanel = lazy(() => import('./widgets/SecurityPanel').then((m) => ({ default: m.SecurityPanel })))
const AutomationsPanel = lazy(() => import('./widgets/AutomationsPanel').then((m) => ({ default: m.AutomationsPanel })))
const MediaControls = lazy(() => import('./widgets/MediaControls').then((m) => ({ default: m.MediaControls })))

// ── Loading Screen ───────────────────────────────────────

function LoadingScreen({ message = 'Carregando' }: { message?: string }) {
  return (
    <div className="loading-screen">
      <div className="loading-spinner" />
      <div className="loading-text">{message}</div>
    </div>
  )
}

// ── Inline small components ─────────────────────────────

function BottomControls() {
  const { activePanel, setActivePanel } = useStore()
  const buttons = [
    { id: 'chat' as const, label: '💬', title: 'Chat' },
    { id: 'memory' as const, label: '🧠', title: 'Memória' },
    { id: 'automations' as const, label: '⚙️', title: 'Automações' },
    { id: 'security' as const, label: '🛡️', title: 'Segurança' },
  ]

  return (
    <div className="bottom-controls">
      {buttons.map((btn) => (
        <button
          key={btn.id}
          className={`control-btn ${activePanel === btn.id ? 'active' : ''}`}
          onClick={() => setActivePanel(activePanel === btn.id ? null : btn.id)}
          title={btn.title}
        >
          {btn.label}
        </button>
      ))}
      {/* MediaControls sem Suspense: se falhar, erro propaga pro ErrorBoundary */}
      <MediaControls />
    </div>
  )
}

function FPSCounter() {
  const fps = useStore((s) => s.fps)
  const frames = useRef(0)
  const lastTime = useRef(performance.now())

  useEffect(() => {
    let rafId: number
    const loop = () => {
      frames.current++
      const now = performance.now()
      if (now - lastTime.current >= 1000) {
        useStore.getState().setFps(frames.current)
        frames.current = 0
        lastTime.current = now
      }
      rafId = requestAnimationFrame(loop)
    }
    rafId = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(rafId)
  }, [])

  return <div className="fps-counter">{fps} FPS</div>
}

// ── Main App ────────────────────────────────────────────

export default function App() {
  const [hydrated, setHydrated] = useState(storeHydrated)

  // ═══ Hooks devem SEMPRE ser chamados na mesma ordem ═══
  // useKernel() é chamado INCONDICIONALMENTE (antes do early return)
  // para não violar as Regras dos Hooks do React.
  // O useEffect dentro de useKernel() só faz fetch se o backend estiver
  // online — durante a reidratação ele apenas define status offline.
  useKernel()

  // Wait for Zustand persist rehydration before showing main UI
  // Prevents flash of unauthenticated state
  useEffect(() => {
    if (hydrated) return
    // Subscribe to Zustand's built-in hydration event
    const unsub = useStore.persist.onFinishHydration(() => setHydrated(true))
    // Safety timeout: show UI after 2s even if storage is slow/corrupt
    const timer = setTimeout(() => setHydrated(true), 2000)
    return () => {
      unsub()
      clearTimeout(timer)
    }
  }, [hydrated])

  if (!hydrated) return <LoadingScreen message="Restaurando sessão..." />

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingScreen />}>
        {/* 3D Scene */}
        <Scene />

        {/* HUD Overlay */}
        <HUD />

        {/* Active Panels */}
        <ChatPanel />
        <MemoryPanel />
        <SecurityPanel />
        <AutomationsPanel />

        {/* Controls */}
        <BottomControls />

        {/* FPS */}
        <FPSCounter />
      </Suspense>
    </ErrorBoundary>
  )
}
