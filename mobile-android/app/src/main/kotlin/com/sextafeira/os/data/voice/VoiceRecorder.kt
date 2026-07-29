package com.sextafeira.os.data.voice

import android.content.Context
import android.media.MediaRecorder
import java.io.File

/**
 * Records audio from the device microphone using MediaRecorder.
 *
 * Output: a WAV file (the kernel expects raw PCM/WAV for faster-whisper).
 * MediaRecorder outputs AMR-NB by default; we convert to WAV or use
 * a high-quality AAC then let the backend handle decoding.
 *
 * For simplicity we use MediaRecorder with AAC and send the raw bytes.
 * The backend's faster-whisper transcriber handles multiple formats.
 */
class VoiceRecorder(private val context: Context) {

    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null

    /** Whether a recording is currently in progress. */
    val isRecording: Boolean
        get() = recorder != null

    /**
     * Start recording from the microphone.
     * @return the temp file path where audio will be written.
     */
    fun start(): File {
        stop()

        val tempDir = context.cacheDir
        val file = File.createTempFile("jarvis_voice_", ".aac", tempDir)
        outputFile = file

        val r = MediaRecorder().apply {
            setAudioSource(MediaRecorder.AudioSource.MIC)
            setOutputFormat(MediaRecorder.OutputFormat.AAC_ADTS)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioSamplingRate(16000)
            setAudioChannels(1)
            setAudioEncodingBitRate(32000)
            setOutputFile(file.absolutePath)
            prepare()
            start()
        }
        recorder = r
        return file
    }

    /**
     * Stop recording and return the audio file bytes.
     * @return the audio file, or null if nothing was recorded.
     */
    fun stop(): ByteArray? {
        val r = recorder ?: return null
        return try {
            r.stop()
            r.release()
            recorder = null
            outputFile?.readBytes()
        } catch (e: Exception) {
            recorder = null
            null
        } finally {
            recorder = null
        }
    }

    /**
     * Get the current maximum amplitude (for visualization).
     * Returns 0 if not recording.
     */
    fun getAmplitude(): Int {
        return recorder?.maxAmplitude ?: 0
    }

    /** Clean up the recorder. Call in onStop / onDestroy. */
    fun release() {
        try {
            recorder?.release()
        } catch (_: Exception) {}
        recorder = null
        outputFile?.delete()
        outputFile = null
    }
}
