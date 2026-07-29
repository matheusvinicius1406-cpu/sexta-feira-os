import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function Lights() {
  const keyLight = useRef<THREE.DirectionalLight>(null!)
  const fillLight = useRef<THREE.DirectionalLight>(null!)
  const rimLight = useRef<THREE.DirectionalLight>(null!)
  const ambientRef = useRef<THREE.AmbientLight>(null!)
  const pointRef = useRef<THREE.PointLight>(null!)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    // Subtle light movement for cinematic feel
    keyLight.current.position.x = Math.sin(t * 0.1) * 5
    keyLight.current.position.y = 6 + Math.sin(t * 0.15) * 2
    fillLight.current.position.x = Math.cos(t * 0.08) * 4
    rimLight.current.position.z = Math.sin(t * 0.12) * 3
    pointRef.current.position.x = Math.sin(t * 0.2) * 3
    pointRef.current.position.z = Math.cos(t * 0.18) * 3
  })

  return (
    <>
      <ambientLight ref={ambientRef} intensity={0.2} color="#4466ff" />
      <directionalLight
        ref={keyLight}
        position={[5, 8, 5]}
        intensity={2}
        color="#4488ff"
        castShadow={false}
      />
      <directionalLight
        ref={fillLight}
        position={[-4, 3, 2]}
        intensity={0.8}
        color="#ff66aa"
      />
      <directionalLight
        ref={rimLight}
        position={[0, -2, -6]}
        intensity={1.2}
        color="#66ccff"
      />
      <pointLight
        ref={pointRef}
        position={[2, 1, 2]}
        intensity={0.5}
        color="#00aaff"
        distance={20}
      />
      <hemisphereLight
        args={['#4488ff', '#001133', 0.3]}
      />
    </>
  )
}
