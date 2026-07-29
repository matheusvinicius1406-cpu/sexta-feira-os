import { useCallback, useRef } from 'react'
import { useStore } from '../store'

/**
 * Connects an Audio element to a Web Audio AnalyserNode and pushes
 * real-time amplitude (0-1) to the store for brain visualization.
 *
 * Call `connect(audioElement)` when playback starts,
 * and `disconnect()` when it ends.
 */
export function useAudioAnalyzer() {
  const ctxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)
  const rafRef = useRef<number>(0)

  const connect = useCallback((audio: HTMLAudioElement) => {
    try {
      // Create or reuse AudioContext
      if (!ctxRef.current) {
        ctxRef.current = new AudioContext()
      }
      const ctx = ctxRef.current
      if (ctx.state === 'suspended') ctx.resume()

      // Create AnalyserNode
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      analyserRef.current = analyser

      // Connect audio element to analyser
      const source = ctx.createMediaElementSource(audio)
      source.connect(analyser)
      analyser.connect(ctx.destination)
      sourceRef.current = source

      const dataArray = new Uint8Array(analyser.frequencyBinCount)

      // RAF loop: read amplitude and push to store
      const update = () => {
        if (!analyserRef.current) {
          useStore.getState().setAudioAmplitude(0)
          return
        }
        analyserRef.current.getByteFrequencyData(dataArray)

        // Average amplitude across all frequency bands, normalized 0-1
        let sum = 0
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i]
        }
        const avg = sum / dataArray.length / 255

        // Smooth and push to store
        const current = useStore.getState().audioAmplitude
        const smoothed = current + (avg - current) * 0.3
        useStore.getState().setAudioAmplitude(smoothed)
        useStore.getState().pushBrainActivity(0.2 + smoothed * 0.8)

        rafRef.current = requestAnimationFrame(update)
      }

      rafRef.current = requestAnimationFrame(update)
    } catch {
      // AudioContext or Web Audio API unavailable — ignore
      useStore.getState().setAudioAmplitude(0)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = 0
    }
    if (sourceRef.current) {
      try { sourceRef.current.disconnect() } catch { /* ignore */ }
      sourceRef.current = null
    }
    if (analyserRef.current) {
      try { analyserRef.current.disconnect() } catch { /* ignore */ }
      analyserRef.current = null
    }
    useStore.getState().setAudioAmplitude(0)
  }, [])

  // Cleanup function for unmount
  const cleanup = useCallback(() => {
    disconnect()
    if (ctxRef.current) {
      ctxRef.current.close().catch(() => {})
      ctxRef.current = null
    }
  }, [disconnect])

  return { connect, disconnect, cleanup }
}
