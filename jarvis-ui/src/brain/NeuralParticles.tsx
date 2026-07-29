import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { neuralVert, neuralFrag } from '../shaders/brain/neuralShaders'

import type { MouseState } from '../hooks/useMouse'

interface Props {
  count?: number
  activity: number
  mouseStateRef: React.RefObject<MouseState>
}

export function NeuralParticles({ count = 8000, activity, mouseStateRef }: Props) {
  const meshRef = useRef<THREE.Points>(null!)
  const materialRef = useRef<THREE.ShaderMaterial>(null!)

  const [positions, colors, sizes, randoms, energies] = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const siz = new Float32Array(count)
    const rnd = new Float32Array(count)
    const eng = new Float32Array(count)

    // Distribute particles in a brain-like ellipsoid shape
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      // Ellipsoid with some random variation
      const rx = 2.8 + (Math.random() - 0.5) * 0.8
      const ry = 2.0 + (Math.random() - 0.5) * 0.6
      const rz = 1.8 + (Math.random() - 0.5) * 0.7

      // More density toward center
      const density = Math.pow(Math.random(), 0.5)
      const r = density

      pos[i * 3] = Math.sin(phi) * Math.cos(theta) * rx * r
      pos[i * 3 + 1] = Math.cos(phi) * ry * r
      pos[i * 3 + 2] = Math.sin(phi) * Math.sin(theta) * rz * r

      // Colors: blue-cyan-purple gradient based on position
      const hue = 0.58 + (pos[i * 3 + 1] / ry) * 0.15
      const color = new THREE.Color().setHSL(hue, 0.9, 0.5)
      col[i * 3] = color.r
      col[i * 3 + 1] = color.g
      col[i * 3 + 2] = color.b

      siz[i] = 0.02 + Math.random() * 0.06
      rnd[i] = Math.random()
      eng[i] = 0.3 + Math.random() * 0.7
    }

    return [pos, col, siz, rnd, eng]
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

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    geo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
    geo.setAttribute('aRandom', new THREE.BufferAttribute(randoms, 1))
    geo.setAttribute('aEnergy', new THREE.BufferAttribute(energies, 1))
    return geo
  }, [positions, colors, sizes, randoms, energies])

  return (
    <points ref={meshRef} geometry={geometry}>
      <shaderMaterial
        ref={materialRef}
        uniforms={uniforms}
        vertexShader={neuralVert}
        fragmentShader={neuralFrag}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}
