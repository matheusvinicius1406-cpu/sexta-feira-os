import { useState, useCallback, useRef, useEffect } from 'react'

export interface MediaState {
  micActive: boolean
  cameraActive: boolean
  stream: MediaStream | null
  error: string | null
  videoRef: React.RefObject<HTMLVideoElement | null>
  isRecording: boolean
  recordingDuration: number
  startRecording: () => Promise<void>
  stopRecording: () => Promise<Blob | null>
}

/**
 * Manages microphone and camera access.
 * Also handles audio recording via MediaRecorder.
 */
export function useMedia() {
  const [micActive, setMicActive] = useState(false)
  const [cameraActive, setCameraActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const streamRef = useRef<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const startMic = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      setMicActive(true)
    } catch (e: any) {
      setError(e.message || 'Microfone não disponível')
    }
  }, [])

  const stopMic = useCallback(() => {
    // Stop recording first if active
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop()
    }
    if (timerRef.current) clearInterval(timerRef.current)
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setMicActive(false)
    setIsRecording(false)
    setRecordingDuration(0)
  }, [])

  const startRecording = useCallback(async () => {
    // Ensure mic is active
    if (!streamRef.current) {
      await startMic()
      // Wait a beat for the stream to be ready
      if (!streamRef.current) return
    }

    chunksRef.current = []
    setRecordingDuration(0)
    setIsRecording(true)

    // Start duration timer
    const startTime = Date.now()
    timerRef.current = setInterval(() => {
      setRecordingDuration(Math.floor((Date.now() - startTime) / 1000))
    }, 200)

    try {
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'
      const recorder = new MediaRecorder(streamRef.current!, { mimeType })

      recorder.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.start(100) // Collect data every 100ms
      recorderRef.current = recorder
    } catch (e: any) {
      setError(`Recorder error: ${e.message}`)
      setIsRecording(false)
    }
  }, [startMic])

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = undefined
      }

      if (!recorderRef.current || recorderRef.current.state === 'inactive') {
        setIsRecording(false)
        setRecordingDuration(0)
        resolve(null)
        return
      }

      recorderRef.current.onstop = () => {
        setIsRecording(false)
        setRecordingDuration(0)

        if (chunksRef.current.length === 0) {
          resolve(null)
          return
        }

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        chunksRef.current = []
        resolve(blob)
      }

      recorderRef.current.stop()
    })
  }, [])

  const startCamera = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
      setCameraActive(true)
    } catch (e: any) {
      setError(e.message || 'Câmera não disponível')
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getVideoTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraActive(false)
  }, [])

  const toggleMic = useCallback(() => {
    if (micActive) {
      stopMic()
    } else {
      startMic()
    }
  }, [micActive, startMic, stopMic])

  const toggleCamera = useCallback(() => {
    cameraActive ? stopCamera() : startCamera()
  }, [cameraActive, startCamera, stopCamera])

  return {
    micActive,
    cameraActive,
    error,
    videoRef,
    toggleMic,
    toggleCamera,
    startMic,
    stopMic,
    startCamera,
    stopCamera,
    // Recording
    isRecording,
    recordingDuration,
    startRecording,
    stopRecording,
  } as MediaState & {
    toggleMic: () => void
    toggleCamera: () => void
    startMic: () => Promise<void>
    stopMic: () => void
    startCamera: () => Promise<void>
    stopCamera: () => void
  }
}
