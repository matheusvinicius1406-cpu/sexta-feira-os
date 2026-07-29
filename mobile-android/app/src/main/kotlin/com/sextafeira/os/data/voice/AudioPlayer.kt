package com.sextafeira.os.data.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileInputStream

/**
 * Plays TTS audio (WAV bytes from Piper) on the device speaker.
 *
 * Manages audio focus and cleans up resources automatically.
 */
class AudioPlayer(private val context: Context) {

    private var player: MediaPlayer? = null
    private var audioManager: AudioManager =
        context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    /** Whether audio is currently playing. */
    val isPlaying: Boolean
        get() = player?.isPlaying ?: false

    /** Play WAV audio bytes on the device speaker. */
    suspend fun play(audioBytes: ByteArray): Unit = withContext(Dispatchers.IO) {
        stop()

        try {
            // Write bytes to a temp file (MediaPlayer needs a file descriptor or URI)
            val tempFile = File(context.cacheDir, "jarvis_tts_${System.nanoTime()}.wav")
            tempFile.writeBytes(audioBytes)

            val player = MediaPlayer().apply {
                setDataSource(FileInputStream(tempFile).fd)
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
                setOnCompletionListener {
                    tempFile.delete()
                    this@AudioPlayer.player = null
                }
                setOnErrorListener { _, what, extra ->
                    tempFile.delete()
                    this@AudioPlayer.player = null
                    true
                }
                prepare()
                start()
            }
            this@AudioPlayer.player = player
        } catch (e: Exception) {
            this@AudioPlayer.player = null
        }
    }

    /** Stop any ongoing playback. */
    fun stop() {
        try {
            player?.stop()
            player?.release()
        } catch (_: Exception) {}
        player = null
    }

    /** Release all resources. */
    fun release() {
        stop()
    }
}
