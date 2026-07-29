import { Bloom, ChromaticAberration, Vignette, Noise, EffectComposer } from '@react-three/postprocessing'
import { useStore } from '../store'

export function PostProcessing() {
  const brainActivity = useStore((s) => s.brainActivity)

  return (
    <EffectComposer multisampling={0}>
      {/* HDR Bloom */}
      <Bloom
        intensity={0.8 + brainActivity * 0.6}
        luminanceThreshold={0.2}
        luminanceSmoothing={0.9}
        mipmapBlur
      />
      <Bloom
        intensity={0.4}
        luminanceThreshold={0.8}
        luminanceSmoothing={0.5}
        mipmapBlur
      />
      <ChromaticAberration offset={[0.001, 0.0005]} />
      <Noise opacity={0.02} />
      <Vignette eskil={false} offset={0.3} darkness={0.6} />
    </EffectComposer>
  )
}
