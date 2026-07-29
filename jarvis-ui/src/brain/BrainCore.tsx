import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { NeuralParticles } from './NeuralParticles'
import { SpeakingWaveform } from './SpeakingWaveform'
import { connectionVert, connectionFrag } from '../shaders/brain/neuralShaders'

import type { MouseState } from '../hooks/useMouse'

interface Props {
  activity: number
  mouseStateRef: React.RefObject<MouseState>
}

function NeuralConnections({ count = 600, activity, mouseStateRef }: { count?: number; activity: number; mouseStateRef: React.RefObject<MouseState> }) {
  const lineRef = useRef<THREE.LineSegments>(null!)
  const materialRef = useRef<THREE.ShaderMaterial>(null!)

  const [positions, energies, randoms] = useMemo(() => {
    const pos: number[] = []
    const ene: number[] = []
    const rnd: number[] = []

    // Generate pairs of connected neurons
    for (let i = 0; i < count; i++) {
      const theta1 = Math.random() * Math.PI * 2
      const phi1 = Math.acos(2 * Math.random() - 1)
      const r1 = Math.pow(Math.random(), 0.4)

      const theta2 = theta1 + (Math.random() - 0.5) * 0.8
      const phi2 = phi1 + (Math.random() - 0.5) * 0.8

      const rx = 2.8, ry = 2.0, rz = 1.8

      pos.push(
        Math.sin(phi1) * Math.cos(theta1) * rx * r1,
        Math.cos(phi1) * ry * r1,
        Math.sin(phi1) * Math.sin(theta1) * rz * r1,
        Math.sin(phi2) * Math.cos(theta2) * rx * r1,
        Math.cos(phi2) * ry * r1,
        Math.sin(phi2) * Math.sin(theta2) * rz * r1,
      )

      const energy = 0.3 + Math.random() * 0.7
      ene.push(energy, energy)
      rnd.push(Math.random(), Math.random())
    }

    return [new Float32Array(pos), new Float32Array(ene), new Float32Array(rnd)]
  }, [count])

  useFrame(({ clock }) => {
    if (materialRef.current) {
      const m = mouseStateRef.current
      materialRef.current.uniforms.uTime.value = clock.getElapsedTime()
      materialRef.current.uniforms.uActivity.value = activity
      materialRef.current.uniforms.uMouse.value.x = m.x
      materialRef.current.uniforms.uMouse.value.y = m.y
      materialRef.current.uniforms.uMouseActive.value = m.down ? 1 : 0.5
    }
  })

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('aEnergy', new THREE.BufferAttribute(energies, 1))
    geo.setAttribute('aRandom', new THREE.BufferAttribute(randoms, 1))
    return geo
  }, [positions, energies, randoms])

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uActivity: { value: activity },
      uPulsePhase: { value: Math.random() * Math.PI * 2 },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uMouseActive: { value: 0 },
    }),
    []
  )

  return (
    <lineSegments ref={lineRef} geometry={geometry}>
      <shaderMaterial
        ref={materialRef}
        uniforms={uniforms}
        vertexShader={connectionVert}
        fragmentShader={connectionFrag}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </lineSegments>
  )
}

function BrainGlow() {
  const meshRef = useRef<THREE.Mesh>(null!)

  useFrame(({ clock }) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(clock.getElapsedTime() * 0.1) * 0.05
      meshRef.current.rotation.y = clock.getElapsedTime() * 0.03
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[3.2, 32, 32]} />
      <meshBasicMaterial
        color="#4488ff"
        transparent
        opacity={0.04}
        wireframe
        depthWrite={false}
      />
    </mesh>
  )
}

function EnergyCore() {
  const meshRef = useRef<THREE.Mesh>(null!)

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const s = 1 + Math.sin(clock.getElapsedTime() * 0.5) * 0.02
      meshRef.current.scale.setScalar(s)
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.8, 16, 16]} />
      <meshBasicMaterial
        color="#88ccff"
        transparent
        opacity={0.3}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

export function BrainCore({ activity, mouseStateRef }: Props) {
  return (
    <group>
      <NeuralParticles count={8000} activity={activity} mouseStateRef={mouseStateRef} />
      <NeuralConnections count={600} activity={activity} mouseStateRef={mouseStateRef} />
      <BrainGlow />
      <EnergyCore />
      <SpeakingWaveform />
    </group>
  )
}
