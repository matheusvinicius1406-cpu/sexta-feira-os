package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.domain.model.ChatMessage
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.api.JarvisChatRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ChatViewModel : ViewModel() {
    
    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error
    
    // API Integration
    private val retrofit = Retrofit.Builder()
        .baseUrl("http://localhost:8000/")  // TODO: Move to config
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    private val apiService: SextaFeiraApi = retrofit.create(SextaFeiraApi::class.java)
    private var authToken: String? = null
    private var conversationId: String? = null
    
    fun setAuthToken(token: String) {
        this.authToken = token
    }
    
    fun sendMessage(content: String) {
        viewModelScope.launch {
            try {
                _isLoading.value = true
                _error.value = null
                
                // Add user message locally
                val userMessage = ChatMessage(
                    id = UUID.randomUUID().toString(),
                    content = content,
                    isFromAssistant = false,
                    timestamp = System.currentTimeMillis()
                )
                
                _messages.value = _messages.value + userMessage
                
                // Verify auth token
                val token = authToken ?: run {
                    _error.value = "Not authenticated"
                    _isLoading.value = false
                    return@launch
                }
                
                // Send to backend API (Jarvis endpoint)
                val request = JarvisChatRequest(
                    message = content,
                    conversation_id = conversationId,
                    stream = false
                )
                
                val response = apiService.jarvisChat(
                    request,
                    "Bearer $token"
                )
                
                // Update conversation ID
                if (conversationId == null) {
                    conversationId = response.conversation_id
                }
                
                // Add assistant response
                val assistantMessage = ChatMessage(
                    id = response.conversation_id ?: UUID.randomUUID().toString(),
                    content = response.response,
                    isFromAssistant = true,
                    timestamp = System.currentTimeMillis()
                )
                
                _messages.value = _messages.value + assistantMessage
                _isLoading.value = false
                
            } catch (e: Exception) {
                _error.value = "Error: ${e.message ?: "Unknown error"}"
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
