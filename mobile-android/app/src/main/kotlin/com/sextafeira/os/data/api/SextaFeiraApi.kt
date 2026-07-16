package com.sextafeira.os.data.api

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/**
 * HTTP DTOs + Retrofit interface for the local kernel (API v1).
 */

data class LoginRequest(
    val email: String,
    val password: String,
)

data class LoginResponse(
    val access_token: String,
    val token_type: String,
    val owner_id: String,
)

data class ChatRequest(
    val message: String,
    val conversation_id: String? = null,
    val device_id: String? = null,
)

data class ChatResponse(
    val reply: String,
    val conversation_id: String,
)

data class HealthResponse(
    val status: String,
    val brain_online: Boolean,
    val brain_model: String,
)

interface SextaFeiraApi {

    @GET("api/v1/health")
    suspend fun health(): HealthResponse

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @POST("api/v1/chat")
    suspend fun chat(
        @Body request: ChatRequest,
        @Header("Authorization") authorization: String,
    ): ChatResponse
}
