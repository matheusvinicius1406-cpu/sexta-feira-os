package com.sextafeira.os.domain.model

data class ChatMessage(
    val id: String,
    val content: String,
    val isFromAssistant: Boolean,
    val timestamp: Long,
    val confidence: Float? = null
)

data class User(
    val id: String,
    val email: String,
    val name: String,
    val createdAt: Long
)

data class AssistantResponse(
    val id: String,
    val message: String,
    val aiProvider: String,
    val metadata: Map<String, Any>? = null
)

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val exception: Exception) : Result<Nothing>()
    object Loading : Result<Nothing>()
}
