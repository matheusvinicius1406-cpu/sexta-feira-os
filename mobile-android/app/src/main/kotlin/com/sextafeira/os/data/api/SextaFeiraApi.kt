package com.sextafeira.os.data.api

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit interface for the Sexta-Feira OS backend API.
 *
 * Base URL is configured in [ApiClient].
 * Authenticated endpoints use Bearer token via [AuthInterceptor].
 */
interface SextaFeiraApi {

    // ── Health ──────────────────────────────────────────

    @GET("api/v1/health")
    suspend fun health(): HealthResponse

    // ── Auth ────────────────────────────────────────────

    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @POST("api/v1/auth/devices/pair")
    suspend fun pairDevice(@Body body: PairRequest): PairResponse

    @GET("api/v1/auth/devices")
    suspend fun listDevices(): List<DeviceInfo>

    @POST("api/v1/auth/devices/{deviceId}/revoke")
    suspend fun revokeDevice(@Path("deviceId") deviceId: String): Map<String, Any>

    // ── Chat ────────────────────────────────────────────

    @POST("api/v1/chat")
    suspend fun chat(@Body body: ChatRequest): ChatResponse

    // ── Conversations ───────────────────────────────────

    @GET("api/v1/chat/conversations")
    suspend fun listConversations(
        @Query("limit") limit: Int = 30,
    ): List<ConversationSummary>

    @GET("api/v1/chat/conversations/{id}")
    suspend fun getConversation(
        @Path("id") conversationId: String,
    ): ConversationDetail

    // ── Memory ──────────────────────────────────────────

    /** List all memory nodes (newest first). */
    @GET("api/v1/memory")
    suspend fun listMemories(
        @Query("limit") limit: Int = 200,
    ): List<MemoryItem>

    /** Teach the kernel a new fact. */
    @POST("api/v1/memory")
    suspend fun teachMemory(@Body body: TeachRequest): MemoryItem

    /** Networked recall — semantic search + graph expansion. */
    @POST("api/v1/memory/recall")
    suspend fun recallMemory(@Body body: RecallRequest): List<MemoryItem>

    /** Forget (delete) a memory node. */
    @DELETE("api/v1/memory/{memoryId}")
    suspend fun forgetMemory(
        @Path("memoryId") memoryId: String,
    ): ForgetResponse

    /** Get the full knowledge graph for visualization. */
    @GET("api/v1/memory/graph")
    suspend fun memoryGraph(
        @Query("limit") limit: Int = 500,
    ): GraphResponse

    // ── Obsidian ────────────────────────────────────────

    @GET("api/v1/obsidian/status")
    suspend fun obsidianStatus(): ObsidianStatus

    // ── Schedule ────────────────────────────────────────

    @POST("api/v1/schedule/reminders")
    suspend fun createReminder(@Body body: ReminderRequest): ReminderResponse

    @GET("api/v1/schedule/reminders")
    suspend fun listReminders(): List<ReminderResponse>

    // ── Connectors ──────────────────────────────────────

    @GET("api/v1/connectors")
    suspend fun listConnectors(): List<ConnectorInfo>
}
