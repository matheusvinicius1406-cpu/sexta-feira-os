package com.sextafeira.os.viewmodel

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.sextafeira.os.data.api.ChatRequest
import com.sextafeira.os.data.api.ChatResponse
import com.sextafeira.os.data.api.Session
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.domain.model.ChatMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import retrofit2.HttpException
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.util.UUID
import javax.inject.Inject

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val savedStateHandle: SavedStateHandle,
    private val api: SextaFeiraApi,
    private val okHttpClient: OkHttpClient,
    private val gson: Gson,
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

    private var conversationId: String? = savedStateHandle["conversation_id"]

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
                // Streaming succeeded — the placeholder was filled inline
                _streamingMessageId.value = null
            }

            _isLoading.value = false
            _streamingContent.value = null
        }
    }

    // ── Streaming via OkHttp direct POST to /api/v1/chat/stream ──

    private suspend fun chatStream(content: String): Boolean {
        val baseUrl = com.sextafeira.os.data.api.ApiClient.baseUrl.trimEnd('/')
        val url = "$baseUrl/api/v1/chat/stream"

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
                override fun onFailure(call: okhttp3.Call, e: IOException) {
                    cont.resumeWithException(e)
                }
            })
            cont.invokeOnCancellation { request.newCall(request).cancel() }
        }

        if (!response.isSuccessful) return false

        val source = response.body?.source() ?: return false
        val sb = StringBuilder()

        // Create placeholder assistant message
        val msgId = UUID.randomUUID().toString()                _streamingMessageId.value = msgId
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

                        // Update the placeholder message inline
                        updatePlaceholderMessage(msgId, sb.toString())
                    }
                }
            }
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
        } catch (e: retrofit2.HttpException) {
            if (e.code() != 401) {
                _error.value = "Erro do servidor (${e.code()})"
            }
        } catch (e: java.net.ConnectException) {
            _error.value = "Não foi possível conectar ao kernel. Verifique se ele está rodando."
        } catch (e: java.net.SocketTimeoutException) {
            _error.value = "O kernel demorou muito para responder. O Ollama está rodando?"
        } catch (e: Exception) {
            _error.value = "Erro: ${e.message ?: "cérebro indisponível"}"
        }
    }

    // ── Helpers ──

    fun clearError() {
        _error.value = null
    }

    fun clearMessages() {
        _messages.value = emptyList()
        conversationId = null
        _streamingContent.value = null
        _streamingMessageId.value = null
    }

    companion object {
        private val JSON_MEDIA_TYPE = MediaType.parse("application/json")!!
    }
}
