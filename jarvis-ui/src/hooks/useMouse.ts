import { useEffect, useRef } from 'react'

export interface MouseState {
  x: number  // -1 to 1, normalized
  y: number  // -1 to 1, normalized
  down: boolean
  velocityX: number
  velocityY: number
}

/**
 * Tracks mouse and touch position, normalized to -1..1 range for 3D scene use.
 * Also tracks click/drag state and velocity for inertia effects.
 */
export function useMouse() {
  const state = useRef<MouseState>({ x: 0, y: 0, down: false, velocityX: 0, velocityY: 0 })
  const prevX = useRef(0)
  const prevY = useRef(0)
  const callbackRef = useRef<((m: MouseState) => void) | null>(null)

  const on = (cb: (m: MouseState) => void) => { callbackRef.current = cb }

  useEffect(() => {
    const handleMove = (clientX: number, clientY: number) => {
      const x = (clientX / window.innerWidth) * 2 - 1
      const y = -(clientY / window.innerHeight) * 2 + 1
      state.current.velocityX = x - prevX.current
      state.current.velocityY = y - prevY.current
      state.current.x = x
      state.current.y = y
      prevX.current = x
      prevY.current = y
      callbackRef.current?.(state.current)
    }

    const onMouseMove = (e: MouseEvent) => handleMove(e.clientX, e.clientY)
    const onMouseDown = () => { state.current.down = true }
    const onMouseUp = () => { state.current.down = false }
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX, e.touches[0].clientY)
      }
    }
    const onTouchStart = () => { state.current.down = true }
    const onTouchEnd = () => { state.current.down = false }

    document.addEventListener('mousemove', onMouseMove, { passive: true })
    document.addEventListener('mousedown', onMouseDown, { passive: true })
    document.addEventListener('mouseup', onMouseUp, { passive: true })
    document.addEventListener('touchmove', onTouchMove, { passive: true })
    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchend', onTouchEnd, { passive: true })

    return () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('mouseup', onMouseUp)
      document.removeEventListener('touchmove', onTouchMove)
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchend', onTouchEnd)
    }
  }, [])

  return { state, on }
}
