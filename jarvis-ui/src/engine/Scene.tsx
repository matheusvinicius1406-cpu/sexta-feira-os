import React, { useEffect, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Camera } from './Camera'
import { Lights } from './Lights'
import { Environment } from './Environment'
import { PostProcessing } from './PostProcessing'
import { BrainCore } from '../brain/BrainCore'
import { useStore } from '../store'
import { useMouse } from '../hooks/useMouse'

function CanvasFallback() {
  const [dots, setDots] = useState('')

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'))
    }, 500)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{
      position: 'fixed', inset: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#000811', color: '#4488ff',
      fontFamily: "'JetBrains Mono', monospace", flexDirection: 'column', gap: 16,
      zIndex: 1,
    }}>
      <div style={{ fontSize: 32, opacity: 0.6 }}>◈</div>
      <div style={{ fontSize: 11, letterSpacing: 4, opacity: 0.4, textTransform: 'uppercase' }}>
        Inicializando{dots}
      </div>
    </div>
  )
}

export function Scene() {
  const brainActivity = useStore((s) => s.brainActivity)
  const [hasError, setError] = useState(false)
  const [canvasReady, setCanvasReady] = useState(false)
  const mountedRef = useRef(true)
  const mouse = useMouse()

  // Safety timeout: if Canvas doesn't become ready in 10s, show error
  // Also sets mountedRef to false on unmount
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!canvasReady && mountedRef.current) {
        console.warn('[JARVIS] Canvas initialization timeout')
        setError(true)
      }
    }, 10000)
    return () => {
      clearTimeout(timer)
      mountedRef.current = false
    }
  }, [canvasReady])

  if (hasError) {
    return (
      <div style={{
        position: 'fixed', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#000811', color: '#4488ff',
        fontFamily: "'JetBrains Mono', monospace", flexDirection: 'column', gap: 12,
        zIndex: 1,
      }}>
        <div style={{ fontSize: 40 }}>⚠</div>
        <div style={{ fontSize: 12, letterSpacing: 2, opacity: 0.5 }}>3D RENDER OFFLINE</div>
        <div style={{ fontSize: 10, opacity: 0.3, maxWidth: 400, textAlign: 'center' }}>
          WebGL não disponível ou ocorreu um erro na renderização 3D.<br />
          A interface HUD ainda está funcional.
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Show loading indicator until Canvas calls onCreated */}
      {!canvasReady && <CanvasFallback />}

      <Canvas
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          stencil: false,
          depth: true,
          failIfMajorPerformanceCaveat: false,
        }}
        camera={{ position: [0, 0, 12], fov: 45, near: 0.1, far: 100 }}
        dpr={[1, 2]}
        performance={{ min: 0.5 }}
        onCreated={(state) => {
          if (!state.gl.capabilities.isWebGL2) {
            console.warn('[JARVIS] WebGL2 not available, falling back to WebGL1')
          }
          if (mountedRef.current) {
            setCanvasReady(true)
          }
        }}
        onError={(err) => {
          console.error('[JARVIS] Canvas error:', err)
          if (mountedRef.current) setError(true)
        }}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          opacity: canvasReady ? 1 : 0,
          transition: 'opacity 0.5s ease-in',
        }}
      >
        <Camera />
        <Lights />
        <Environment />
        <BrainCore
          activity={brainActivity}
          mouseStateRef={mouse.state}
        />
        <PostProcessing />
      </Canvas>
    </>
  )
}
