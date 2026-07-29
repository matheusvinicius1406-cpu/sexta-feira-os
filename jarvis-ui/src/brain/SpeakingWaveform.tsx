import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useStore } from '../store'

/**
 * Concentric waveform rings around the brain that pulse with TTS audio amplitude.
 * All rings share a single uniforms object for synchronized updates.
 */
export function SpeakingWaveform() {
  const ringsRef = useRef<THREE.Group>(null!)
  const amplitudes = useRef<number[]>(new Array(4).fill(0))

  // Shared uniforms for ALL rings — useFrame updates this, affecting all rings
  const sharedUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uAmplitude: { value: 0 },
      uAmps: { value: new THREE.Vector4(0, 0, 0, 0) },
    }),
    [],
  )

  // Pre-create full LineLoop objects (geometry + material) — memoized, zero allocations per render
  const lineLoops = useMemo(() => {
    return Array.from({ length: 4 }, (_, i) => {
      const radius = 3.8 + i * 0.8
      const segments = 48 + i * 12
      const positions: number[] = []
      const angles: number[] = []

      for (let j = 0; j <= segments; j++) {
        const theta = (j / segments) * Math.PI * 2
        positions.push(Math.cos(theta) * radius, 0, Math.sin(theta) * radius)
        angles.push(theta)
      }

      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
      geo.setAttribute('aAngle', new THREE.BufferAttribute(new Float32Array(angles), 1))

      const mat = new THREE.ShaderMaterial({
        uniforms: sharedUniforms,
        vertexShader: waveformVert,
        fragmentShader: waveformFrag,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })

      return new THREE.LineLoop(geo, mat)
    })
  }, [])

  // Dispose Three.js objects on unmount
  useEffect(() => {
    return () => {
      lineLoops.forEach((loop) => {
        loop.geometry.dispose()
        loop.material.dispose()
      })
    }
  }, [lineLoops])

  useFrame(({ clock }) => {
    const amp = useStore.getState().audioAmplitude
    const time = clock.getElapsedTime()

    // Smooth amplitude transitions per ring (cascade)
    for (let i = 0; i < 4; i++) {
      const target = i === 0 ? amp : amplitudes.current[i - 1]
      amplitudes.current[i] += (target - amplitudes.current[i]) * 0.1
    }

    // Update shared uniforms — affects all rings at once
    sharedUniforms.uTime.value = time
    sharedUniforms.uAmplitude.value = amp
    sharedUniforms.uAmps.value.set(
      amplitudes.current[0],
      amplitudes.current[1],
      amplitudes.current[2],
      amplitudes.current[3],
    )

    // Gentle auto-rotation
    if (ringsRef.current) {
      ringsRef.current.rotation.y = time * 0.15
      ringsRef.current.rotation.x = Math.sin(time * 0.1) * 0.05
    }
  })

  return (
    <group ref={ringsRef}>
      {lineLoops.map((loop, i) => (
        <primitive key={i} object={loop} />
      ))}
    </group>
  )
}

const waveformVert = `
uniform float uTime;
uniform float uAmplitude;
uniform vec4 uAmps;

attribute float aAngle;

varying float vGlow;

void main() {
  vec3 pos = position;

  // Map ring radius (stored in XZ length) to a ring index 0-3
  float radius = length(pos.xz);
  float ringIdx = clamp(floor((radius - 3.5) / 0.8), 0.0, 3.0);
  float amp = uAmps[int(ringIdx)];

  // Three wave frequencies for organic motion
  float wave  = sin(aAngle * 6.0 - uTime * 3.0) * amp * 0.6;
  float wave2 = sin(aAngle * 12.0 + uTime * 2.0) * amp * 0.3;
  float wave3 = cos(aAngle * 8.0 - uTime * 4.0) * amp * 0.4;
  pos.y = (wave + wave2 + wave3) * 0.5;

  // Radial pulse — ring expands/contracts with beat
  float pulse = 1.0 + sin(aAngle * 4.0 + uTime * 2.0) * amp * 0.08;
  pos.x *= pulse;
  pos.z *= pulse;

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  vGlow = amp * (0.5 + 0.5 * sin(uTime * 2.0 + aAngle * 3.0));
}
`

const waveformFrag = `
uniform float uAmplitude;

varying float vGlow;

void main() {
  float intensity = 0.15 + vGlow * 0.85;
  vec3 color = mix(
    vec3(0.08, 0.25, 0.7),    // deep blue
    vec3(0.4, 0.85, 1.0),     // bright cyan
    intensity
  );

  float alpha = intensity * 0.45;
  float hdr = 1.0 + intensity * 2.5;

  gl_FragColor = vec4(color * hdr, alpha);
}
`
