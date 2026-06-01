package com.sextafeira.os.data.api

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Header

/**
 * HTTP DTOs for API communication with Sexta-Feira OS Backend
 */

data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    val access_token: String,
    val user_id: String,
    val token_type: String = "bearer"
)

data class JarvisChatRequest(
    val message: String,
    val conversation_id: String? = null,
    val stream: Boolean = false
)

data class JarvisChatResponse(
    val response: String,
    val provider: String,
    val conversation_id: String? = null,
    val metadata: Map<String, Any> = emptyMap()
)

data class JarvisStatus(
    val status: String,
    val version: String,
    val gemini_ready: Boolean,
    val memory_ready: Boolean
)

/**
 * Retrofit API Interface for Jarvis Android Integration
 */
interface SextaFeiraApi {
    
    // Health & Status endpoints
    @GET("/api/v1/health")
    suspend fun health(): Map<String, String>
    
    @GET("/api/v1/jarvis/status")
    suspend fun jarvisStatus(
        @Header("Authorization") token: String
    ): JarvisStatus
    
    // Authentication
    @POST("/api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse
    
    // Jarvis Chat (main endpoint for Android)
    @POST("/api/v1/jarvis/chat")
    suspend fun jarvisChat(
        @Body request: JarvisChatRequest,
        @Header("Authorization") token: String
    ): JarvisChatResponse
}
