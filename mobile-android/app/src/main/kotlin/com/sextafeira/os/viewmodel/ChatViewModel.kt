package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.data.api.ApiClient
import com.sextafeira.os.data.api.ChatRequest
import com.sextafeira.os.data.api.Session
import com.sextafeira.os.domain.model.ChatMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID

class ChatViewModel : ViewModel() {

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    private var conversationId: String? = null

    fun sendMessage(content: String) {
        val bearer = Session.bearer
        if (bearer == null) {
            _error.value = "Sessão expirada — entre novamente."
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            _messages.value = _messages.value + ChatMessage(
                id = UUID.randomUUID().toString(),
                content = content,
                isFromAssistant = false,
                timestamp = System.currentTimeMillis(),
            )

            try {
                val response = ApiClient.api.chat(
                    ChatRequest(message = content, conversation_id = conversationId),
                    bearer,
                )
                conversationId = response.conversation_id
                _messages.value = _messages.value + ChatMessage(
                    id = UUID.randomUUID().toString(),
                    content = response.reply,
                    isFromAssistant = true,
                    timestamp = System.currentTimeMillis(),
                )
            } catch (e: Exception) {
                _error.value = "Erro: ${e.message ?: "cérebro indisponível (Ollama ligado?)"}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun clearError() {
        _error.value = null
    }

    fun clearMessages() {
        _messages.value = emptyList()
        conversationId = null
    }
}
