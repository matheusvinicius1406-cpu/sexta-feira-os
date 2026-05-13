package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.domain.model.ChatMessage
import com.sextafeira.os.domain.model.Result
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
    
    fun sendMessage(content: String) {
        viewModelScope.launch {
            try {
                _isLoading.value = true
                
                // Add user message locally
                val userMessage = ChatMessage(
                    id = UUID.randomUUID().toString(),
                    content = content,
                    isFromAssistant = false,
                    timestamp = System.currentTimeMillis()
                )
                
                _messages.value = _messages.value + userMessage
                
                // TODO: Send to backend API
                // val response = apiService.chat(ChatRequest(content))
                // val assistantMessage = ChatMessage(...)
                // _messages.value = _messages.value + assistantMessage
                
                _isLoading.value = false
            } catch (e: Exception) {
                _error.value = e.message
                _isLoading.value = false
            }
        }
    }
    
    fun clearError() {
        _error.value = null
    }
}
