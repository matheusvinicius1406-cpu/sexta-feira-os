package com.sextafeira.os.data.api

import com.sextafeira.os.domain.model.ChatMessage
import com.sextafeira.os.domain.model.AssistantResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Header

data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    val token: String,
    val userId: String
)

data class ChatRequest(
    val message: String,
    val provider: String = "openai"
)

interface SextaFeiraApi {
    @POST("/api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse
    
    @GET("/api/v1/health")
    suspend fun health(): Map<String, String>
    
    @POST("/api/v1/chat")
    suspend fun chat(
        @Body request: ChatRequest,
        @Header("Authorization") token: String
    ): AssistantResponse
    
    @GET("/api/v1/memory")
    suspend fun getMemory(
        @Header("Authorization") token: String
    ): Map<String, Any>
}
