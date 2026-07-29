import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'

function HolographicGrid() {
  const gridRef = useRef<THREE.GridHelper>(null!)
  const gridHelper = new THREE.GridHelper(30, 60, 0x4488ff, 0x2244aa)
  gridHelper.material.transparent = true
  gridHelper.material.opacity = 0.15
  gridHelper.position.y = -3.5

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    gridHelper.position.z = (t * 0.3) % 1
    gridHelper.material.opacity = 0.1 + Math.sin(t * 0.5) * 0.05
  })

  return <primitive object={gridHelper} />
}

function OrbitingRings() {
  const groupRef = useRef<THREE.Group>(null!)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    groupRef.current.rotation.x = Math.sin(t * 0.1) * 0.1
    groupRef.current.rotation.y = t * 0.05
    groupRef.current.rotation.z = Math.cos(t * 0.08) * 0.05
  })

  const rings = Array.from({ length: 3 }, (_, i) => {
    const radius = 6 + i * 1.5
    const geometry = new THREE.RingGeometry(radius - 0.02, radius, 80)
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color().setHSL(0.6 + i * 0.05, 0.8, 0.3 + i * 0.1),
      transparent: true,
      opacity: 0.08 + i * 0.02,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
    const mesh = new THREE.Mesh(geometry, material)
    mesh.rotation.x = Math.PI / 3 + i * 0.2
    return <primitive key={i} object={mesh} />
  })

  return <group ref={groupRef}>{rings}</group>
}

function AtmosphericParticles() {
  const count = 200
  const positions = new Float32Array(count * 3)
  const sizes = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 40
    positions[i * 3 + 1] = (Math.random() - 0.5) * 20
    positions[i * 3 + 2] = (Math.random() - 0.5) * 40 - 5
    sizes[i] = Math.random() * 2 + 0.5
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  const material = new THREE.PointsMaterial({
    color: '#4488ff',
    size: 0.03,
    transparent: true,
    opacity: 0.3,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  })

  const points = new THREE.Points(geometry, material)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const pos = points.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 1] += Math.sin(t * 0.1 + i) * 0.001
    }
    points.geometry.attributes.position.needsUpdate = true
  })

  return <primitive object={points} />
}

export function Environment() {
  return (
    <>
      <fog attach="fog" args={['#000811', 15, 35]} />
      <color attach="background" args={['#000811']} />
      <HolographicGrid />
      <OrbitingRings />
      <AtmosphericParticles />
    </>
  )
}
