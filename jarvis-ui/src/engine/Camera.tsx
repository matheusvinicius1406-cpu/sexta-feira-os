import { useFrame, useThree } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'

export function Camera() {
  const { camera } = useThree()
  const angle = useRef(0)
  const height = useRef(0)
  const target = useRef(new THREE.Vector3(0, 0, 0))
  const tempVec = useRef(new THREE.Vector3())

  // Mouse/touch drag state for interactive orbit
  const dragStart = useRef<{ x: number; y: number } | null>(null)
  const dragAngle = useRef(0)
  const dragHeight = useRef(0)

  // Listen for mouse/touch drag on the canvas
  useFrame(({ gl }, delta) => {
    const canvas = gl.domElement

    const handleDrag = (clientX: number, clientY: number, isStart: boolean, isEnd: boolean) => {
      if (isStart) {
        dragStart.current = { x: clientX, y: clientY }
      } else if (isEnd) {
        dragStart.current = null
      } else if (dragStart.current) {
        const dx = (clientX - dragStart.current.x) * 0.005
        const dy = (clientY - dragStart.current.y) * 0.005
        dragAngle.current += dx
        dragHeight.current += dy
        dragStart.current = { x: clientX, y: clientY }
      }
    }

    const onMouseDown = (e: MouseEvent) => handleDrag(e.clientX, e.clientY, true, false)
    const onMouseMove = (e: MouseEvent) => handleDrag(e.clientX, e.clientY, false, false)
    const onMouseUp = () => handleDrag(0, 0, false, true)
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) handleDrag(e.touches[0].clientX, e.touches[0].clientY, true, false)
    }
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1) handleDrag(e.touches[0].clientX, e.touches[0].clientY, false, false)
    }
    const onTouchEnd = () => handleDrag(0, 0, false, true)

    canvas.addEventListener('mousedown', onMouseDown)
    canvas.addEventListener('mousemove', onMouseMove)
    canvas.addEventListener('mouseup', onMouseUp)
    canvas.addEventListener('mouseleave', onMouseUp)
    canvas.addEventListener('touchstart', onTouchStart, { passive: true })
    canvas.addEventListener('touchmove', onTouchMove, { passive: true })
    canvas.addEventListener('touchend', onTouchEnd, { passive: true })

    // Combine auto-orbit with drag offset
    const autoAngle = delta * 0.06
    const autoHeight = delta * 0.02
    angle.current += autoAngle
    height.current += autoHeight

    const finalAngle = angle.current + dragAngle.current
    const finalHeight = height.current + dragHeight.current
    const radius = 10 + Math.sin(finalHeight * 0.3) * 1.5
    const x = Math.sin(finalAngle) * radius
    const z = Math.cos(finalAngle) * radius
    const y = 1.5 + Math.sin(finalHeight * 0.5) * 0.8

    camera.position.lerp(tempVec.current.set(x, y, z), delta * 0.8)
    camera.lookAt(target.current)

    // Cleanup listeners on next frame (they're re-attached each frame)
    return () => {
      canvas.removeEventListener('mousedown', onMouseDown)
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseup', onMouseUp)
      canvas.removeEventListener('mouseleave', onMouseUp)
      canvas.removeEventListener('touchstart', onTouchStart as EventListener)
      canvas.removeEventListener('touchmove', onTouchMove as EventListener)
      canvas.removeEventListener('touchend', onTouchEnd as EventListener)
    }
  })

  return null
}
