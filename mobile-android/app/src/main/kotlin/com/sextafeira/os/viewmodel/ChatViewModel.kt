package com.sextafeira.os.viewmodel

import android.app.Application
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.sextafeira.os.data.api.ApiClient
import com.sextafeira.os.data.api.ChatRequest
import com.sextafeira.os.data.api.Session
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.api.VoiceChatResponse
import com.sextafeira.os.data.api.VoiceStatusResponse
import com.sextafeira.os.data.voice.VoiceManager
import com.sextafeira.os.domain.model.ChatMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import java.io.File
import java.util.UUID
import javax.inject.Inject

// ── Voice UI State ────────────────────────────────────────

data class VoiceUiState(
    val isRecording: Boolean = false,
    val isPlaying: Boolean = false,
    val amplitude: Int = 0,          // 0-32767 for mic visualizer
    val sttAvailable: Boolean = false,
    val ttsAvailable: Boolean = false,
    val voiceEnabled: Boolean = true,
    val transcript: String? = null,  // shows what was heard after recording
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val savedStateHandle: SavedStateHandle,
    private val api: SextaFeiraApi,
    private val okHttpClient: OkHttpClient,
    private val gson: Gson,
    private val voiceManager: VoiceManager,
) : ViewModel() {

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _streamingContent = MutableStateFlow<String?>(null)
    val streamingContent: StateFlow<String?> = _streamingContent

    private val _streamingMessageId = MutableStateFlow<String?>(null)
    val streamingMessageId: StateFlow<String?> = _streamingMessageId

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    private val _voiceState = MutableStateFlow(VoiceUiState())
    val voiceState: StateFlow<VoiceUiState> = _voiceState

    private var conversationId: String? = savedStateHandle["conversation_id"]

    init {
        // Check voice availability on startup
        viewModelScope.launch {
            try {
                val status = api.voiceStatus()
                _voiceState.value = _voiceState.value.copy(
                    sttAvailable = status.sttAvailable,
                    ttsAvailable = status.ttsAvailable,
                    voiceEnabled = status.enabled,
                )
            } catch (_: Exception) {}
        }
    }

    // ── Text Chat ─────────────────────────────────────────

    fun sendMessage(content: String) {
        val bearer = Session.bearer
        if (bearer == null) {
            _error.value = "Sessão expirada — entre novamente."
            return
        }

        val userMessage = ChatMessage(
            id = UUID.randomUUID().toString(),
            content = content,
            isFromAssistant = false,
            timestamp = System.currentTimeMillis(),
        )
        _messages.value = _messages.value + userMessage

        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            val streamSuccess = try {
                chatStream(content)
            } catch (_: Exception) {
                false
            }

            if (!streamSuccess) {
                chatNonStreaming(content)
            } else {
                _streamingMessageId.value = null
            }

            _isLoading.value = false
            _streamingContent.value = null
        }
    }

    // ── Voice Chat ────────────────────────────────────────

    /** Start recording voice. */
    fun startVoiceRecording() {
        if (!_voiceState.value.sttAvailable) {
            _error.value = "STT (reconhecimento de voz) não disponível no servidor"
            return
        }
        voiceManager.startRecording()
        _voiceState.value = _voiceState.value.copy(
            isRecording = true,
            transcript = null,
        )

        // Poll amplitude for visualizer while recording
        viewModelScope.launch {
            while (_voiceState.value.isRecording) {
                _voiceState.value = _voiceState.value.copy(
                    amplitude = voiceManager.getAmplitude(),
                )
                delay(80)
            }
            _voiceState.value = _voiceState.value.copy(amplitude = 0)
        }
    }

    /** Stop recording and send voice to the kernel for the full loop. */
    fun stopVoiceRecording(speakReply: Boolean = true) {
        if (!_voiceState.value.isRecording) return

        // Capture the final amplitude before stopping
        _voiceState.value = _voiceState.value.copy(
            isRecording = false,
            amplitude = 0,
        )

        val bearer = Session.bearer
        if (bearer == null) {
            _error.value = "Sessão expirada — entre novamente."
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                // Use the full voice chat endpoint: transcribe → think → reply
                val result = voiceManager.voiceChat(speakReply)

                if (result.transcript != null) {
                    // Show what was heard
                    _voiceState.value = _voiceState.value.copy(transcript = result.transcript)

                    // Add user message (the transcript)
                    _messages.value = _messages.value + ChatMessage(
                        id = UUID.randomUUID().toString(),
                        content = "🎤 $result.transcript",
                        isFromAssistant = false,
                        timestamp = System.currentTimeMillis(),
                    )

                    // Update conversation ID
                    if (result.conversationId != null) {
                        conversationId = result.conversationId
                    }

                    // Add assistant reply
                    _messages.value = _messages.value + ChatMessage(
                        id = UUID.randomUUID().toString(),
                        content = result.reply,
                        isFromAssistant = true,
                        timestamp = System.currentTimeMillis(),
                    )
                } else {
                    _error.value = "Não foi possível transcrever o áudio"
                }

                _voiceState.value = _voiceState.value.copy(isPlaying = voiceManager.isPlaying)

            } catch (e: Exception) {
                _error.value = "Erro na comunicação por voz: ${e.message ?: "desconhecido"}"
            }

            _isLoading.value = false
        }
    }

    /** Speak the given text using TTS (e.g., last assistant reply). */
    fun speakText(text: String) {
        if (!_voiceState.value.ttsAvailable) return
        viewModelScope.launch {
            _voiceState.value = _voiceState.value.copy(isPlaying = true)
            voiceManager.speak(text)
            _voiceState.value = _voiceState.value.copy(isPlaying = false)
        }
    }

    /** Stop any ongoing TTS playback. */
    fun stopSpeaking() {
        voiceManager.release()
        _voiceState.value = _voiceState.value.copy(isPlaying = false)
    }

    // ── Streaming ────────────────────────────────────────

    private suspend fun chatStream(content: String): Boolean {
        val baseUrl = ApiClient.baseUrl.trimEnd('/')
        val url = "$baseUrl/api/v1/chat/stream"
        val bearer = Session.bearer ?: return false

        val bodyMap = mutableMapOf<String, String>("message" to content)
        conversationId?.let { bodyMap["conversation_id"] = it }
        val jsonBody = gson.toJson(bodyMap)

        val request = Request.Builder()
            .url(url)
            .post(RequestBody.create(JSON_MEDIA_TYPE, jsonBody))
            .header("Authorization", bearer)
            .build()

        val response = kotlinx.coroutines.suspendCancellableCoroutine<Response> { cont ->
            okHttpClient.newCall(request).enqueue(object : okhttp3.Callback {
                override fun onResponse(call: okhttp3.Call, resp: Response) {
                    cont.resume(resp) {}
                }
                override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                    cont.resumeWithException(e)
                }
            })
            cont.invokeOnCancellation { request.newCall(request).cancel() }
        }

        if (!response.isSuccessful) return false

        val source = response.body?.source() ?: return false
        val sb = StringBuilder()

        val msgId = UUID.randomUUID().toString()
        _streamingMessageId.value = msgId
        _messages.value = _messages.value + ChatMessage(
            id = msgId,
            content = "",
            isFromAssistant = true,
            timestamp = System.currentTimeMillis(),
        )

        source.use { src ->
            while (!src.exhausted()) {
                val line = src.readUtf8Line() ?: break
                if (!line.startsWith("data: ")) continue
                val data = line.removePrefix("data: ").trim()

                when {
                    data.contains("\"conversation_id\"") -> {
                        conversationId = try {
                            val parsed = gson.fromJson(data, Map::class.java)
                            parsed["conversation_id"]?.toString()
                        } catch (_: Exception) { null }
                    }
                    data.contains("\"done\"") && data.contains("true") -> break
                    data.contains("\"chunk\"") -> {
                        val chunk = try {
                            val parsed = gson.fromJson(data, Map::class.java)
                            parsed["chunk"]?.toString() ?: continue
                        } catch (_: Exception) { continue }

                        sb.append(chunk)
                        _streamingContent.value = sb.toString()
                        updatePlaceholderMessage(msgId, sb.toString())
                    }
                }
            }
        }

        // Auto-speak the complete reply if TTS is available
        if (sb.isNotEmpty() && _voiceState.value.ttsAvailable && _voiceState.value.voiceEnabled) {
            voiceManager.speak(sb.toString())
        }

        return true
    }

    private fun updatePlaceholderMessage(id: String, content: String) {
        val msgs = _messages.value.toMutableList()
        val idx = msgs.indexOfLast { it.id == id }
        if (idx >= 0) {
            msgs[idx] = msgs[idx].copy(content = content)
            _messages.value = msgs
        }
    }

    // ── Fallback non-streaming ──

    private suspend fun chatNonStreaming(content: String) {
        try {
            val response = api.chat(
                ChatRequest(message = content, conversationId = conversationId),
            )
            conversationId = response.conversationId
            _messages.value = _messages.value + ChatMessage(
                id = UUID.randomUUID().toString(),
                content = response.reply,
                isFromAssistant = true,
                timestamp = System.currentTimeMillis(),
            )

            // Auto-speak if TTS available
            if (_voiceState.value.ttsAvailable && _voiceState.value.voiceEnabled) {
                voiceManager.speak(response.reply)
            }
        } catch (e: retrofit2.HttpException) {
            if (e.code() != 401) _error.value = "Erro do servidor (${e.code()})"
        } catch (e: java.net.ConnectException) {
            _error.value = "Não foi possível conectar ao kernel. Verifique se ele está rodando."
        } catch (e: java.net.SocketTimeoutException) {
            _error.value = "O kernel demorou muito para responder. O Ollama está rodando?"
        } catch (e: Exception) {
            _error.value = "Erro: ${e.message ?: "cérebro indisponível"}"
        }
    }

    // ── Helpers ──

    fun clearError() { _error.value = null }
    fun clearMessages() {
        _messages.value = emptyList()
        conversationId = null
        _streamingContent.value = null
        _streamingMessageId.value = null
    }

    override fun onCleared() {
        super.onCleared()
        voiceManager.release()
    }

    companion object {
        private val JSON_MEDIA_TYPE = MediaType.parse("application/json")!!
    }
}
