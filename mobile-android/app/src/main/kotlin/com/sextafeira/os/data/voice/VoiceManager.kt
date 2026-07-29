package com.sextafeira.os.data.voice

import android.content.Context
import android.net.Uri
import com.sextafeira.os.data.api.ApiClient
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.api.VoiceChatResponse
import com.sextafeira.os.data.api.VoiceStatusResponse
import okhttp3.MediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import java.io.File
import javax.inject.Singleton

/**
 * Coordinates voice recording, STT transmission, and TTS playback.
 *
 * Provides a high-level API:
 *   - record() / stopRecording() → sends audio to STT
 *   - speak(text) → requests TTS and plays it
 *   - voiceChat() → full loop: record → transcribe → chat → speak reply
 */
@Singleton
class VoiceManager(
    private val context: Context,
    private val api: SextaFeiraApi,
) {
    private val recorder = VoiceRecorder(context)
    private val player = AudioPlayer(context)

    /** Current recording state. */
    var isRecording: Boolean = false
        private set

    /** Current playback state. */
    var isPlaying: Boolean = false
        private set

    // ── Status ───────────────────────────────────────────

    /** Check which voice engines are available on the server. */
    suspend fun checkStatus(): VoiceStatusResponse {
        return api.voiceStatus()
    }

    // ── Recording ────────────────────────────────────────

    /** Start recording from the microphone. */
    fun startRecording() {
        recorder.start()
        isRecording = true
    }

    /** Get current amplitude (0-32767) for visualization. */
    fun getAmplitude(): Int = recorder.getAmplitude()

    /**
     * Stop recording and send the audio to the kernel for transcription.
     * @return transcribed text, or null on failure.
     */
    suspend fun stopAndTranscribe(): String? {
        val audioBytes = recorder.stop()
        isRecording = false
        if (audioBytes == null || audioBytes.isEmpty()) return null

        return try {
            // Write bytes to a temp file for multipart upload
            val tempFile = File(context.cacheDir, "upload_${System.nanoTime()}.aac")
            tempFile.writeBytes(audioBytes)

            val requestBody = RequestBody.create(MediaType.parse("audio/aac"), tempFile)
            val part = MultipartBody.Part.createFormData("file", tempFile.name, requestBody)

            val response = api.transcribeAudio(part)
            tempFile.delete()
            response.text
        } catch (e: Exception) {
            null
        }
    }

    // ── TTS ──────────────────────────────────────────────

    /**
     * Request the kernel to synthesize text and play it.
     */
    suspend fun speak(text: String) {
        try {
            val response = api.speakText(com.sextafeira.os.data.api.SpeakRequest(text = text))
            val audioBytes = response.bytes()
            if (audioBytes.isNotEmpty()) {
                isPlaying = true
                player.play(audioBytes)
                isPlaying = false
            }
        } catch (_: Exception) {
            isPlaying = false
        }
    }

    // ── Full Voice Chat ──────────────────────────────────

    /**
     * Full voice loop: record → transcribe → think → speak reply.
     * @param speakReply whether the kernel should speak the reply (TTS).
     * @return the response with transcript, reply text, and optional base64 audio.
     */
    suspend fun voiceChat(speakReply: Boolean = true): VoiceChatResult {
        val audioBytes = recorder.stop()
        isRecording = false
        if (audioBytes == null || audioBytes.isEmpty()) {
            return VoiceChatResult(null, "Nada gravado", null)
        }

        return try {
            val tempFile = File(context.cacheDir, "vchat_${System.nanoTime()}.aac")
            tempFile.writeBytes(audioBytes)

            val requestBody = RequestBody.create(MediaType.parse("audio/aac"), tempFile)
            val part = MultipartBody.Part.createFormData("file", tempFile.name, requestBody)
            val speakBody = RequestBody.create(MediaType.parse("text/plain"), speakReply.toString())

            val response = api.voiceChat(part, speakBody)
            tempFile.delete()

            // Auto-play TTS if audio was returned
            if (response.audioWavBase64 != null) {
                val wavBytes = android.util.Base64.decode(response.audioWavBase64, android.util.Base64.DEFAULT)
                if (wavBytes.isNotEmpty()) {
                    isPlaying = true
                    player.play(wavBytes)
                    isPlaying = false
                }
            }

            VoiceChatResult(
                transcript = response.transcript,
                reply = response.reply,
                conversationId = response.conversationId,
            )
        } catch (e: Exception) {
            VoiceChatResult(null, "Erro: ${e.message}", null)
        }
    }

    // ── Cleanup ──────────────────────────────────────────

    /** Stop any ongoing recording or playback. Call in ViewModel.onCleared(). */
    fun release() {
        recorder.release()
        player.release()
        isRecording = false
        isPlaying = false
    }
}

/** Result of a full voice chat cycle. */
data class VoiceChatResult(
    val transcript: String?,
    val reply: String,
    val conversationId: String?,
)
