package com.sextafeira.os.data.api

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

// ─────────────────────────────── DTOs ───────────────────────────────

// -- Auth --
data class LoginRequest(
    val email: String,
    val password: String,
)

data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("owner_id") val ownerId: String,
)

// -- Chat --
data class ChatRequest(
    val message: String,
    @SerializedName("conversation_id") val conversationId: String? = null,
    @SerializedName("device_id") val deviceId: String? = null,
)

data class ChatResponse(
    val reply: String,
    @SerializedName("conversation_id") val conversationId: String,
)

// -- Health --
data class HealthResponse(
    val status: String,
    @SerializedName("brain_online") val brainOnline: Boolean,
    @SerializedName("brain_model") val brainModel: String,
)

// -- Conversations --
data class ConversationSummary(
    val id: String,
    val title: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null,
    @SerializedName("message_count") val messageCount: Int = 0,
)

data class ConversationDetail(
    val id: String,
    val title: String? = null,
    val messages: List<MessageItem> = emptyList(),
)

data class MessageItem(
    val role: String,
    val content: String,
    @SerializedName("created_at") val createdAt: String? = null,
)

// -- Memory --
data class MemoryRequest(
    val content: String,
    val kind: String = "fact",
    val title: String? = null,
)

data class MemoryResponse(
    val id: String,
    val content: String,
    val kind: String,
    val title: String? = null,
    val importance: Float = 0.5f,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class MemoryRecallRequest(
    val query: String,
    val networked: Boolean = false,
)

data class LinkRequest(
    @SerializedName("target_id") val targetId: String,
    val relation: String = "related",
)

data class GraphResponse(
    val nodes: List<GraphNode> = emptyList(),
    val edges: List<GraphEdge> = emptyList(),
)

data class GraphNode(
    val id: String,
    val title: String,
    val kind: String = "fact",
)

data class GraphEdge(
    val source: String,
    val target: String,
    val relation: String = "related",
)

// -- Schedule --
data class ScheduleRequest(
    val kind: String = "reminder",
    val text: String,
    @SerializedName("in_days") val inDays: Int? = null,
    @SerializedName("in_seconds") val inSeconds: Int? = null,
    val device: String? = null,
    @SerializedName("recurrence_seconds") val recurrenceSeconds: Int? = null,
)

data class ScheduleResponse(
    val id: String,
    val kind: String,
    val text: String? = null,
    val status: String = "pending",
    @SerializedName("due_at") val dueAt: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)

// -- Voice --
data class VoiceStatus(
    @SerializedName("stt_available") val sttAvailable: Boolean = false,
    @SerializedName("tts_available") val ttsAvailable: Boolean = false,
)

data class SpeakRequest(
    val text: String,
)

// -- Actions --
data class ActionDispatchRequest(
    val device: String,
    val action: String,
    val params: Map<String, String> = emptyMap(),
)

data class ActionResponse(
    val ok: Boolean,
    val delivered: Boolean = false,
    @SerializedName("command_id") val commandId: String? = null,
)

data class ActionItem(
    val id: String,
    val action: String,
    val status: String,
    val params: Map<String, String>? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)

// -- Connectors --
data class ConnectorRequest(
    val name: String,
    val description: String,
    val url: String,
    val method: String = "GET",
)

data class ConnectorResponse(
    val name: String,
    val description: String,
    val url: String,
    val method: String = "GET",
    val enabled: Boolean = true,
)

data class ConnectorCallRequest(
    val params: Map<String, String> = emptyMap(),
)

data class ConnectorCallResponse(
    val ok: Boolean,
    val data: Map<String, Any>? = null,
    val error: String? = null,
)

// ─────────────────────────────── Retrofit Interface ───────────────────────────────

interface SextaFeiraApi {

    // -- Health --
    @GET("api/v1/health")
    suspend fun health(): HealthResponse

    // -- Auth --
    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @POST("api/v1/auth/devices/pair")
    suspend fun pairDevice(
        @Body request: Map<String, String>,
        @Header("Authorization") authorization: String,
    ): Map<String, String>

    // -- Chat --
    @POST("api/v1/chat")
    suspend fun chat(
        @Body request: ChatRequest,
        @Header("Authorization") authorization: String,
    ): ChatResponse

    // -- Conversations --
    @GET("api/v1/chat/conversations")
    suspend fun listConversations(
        @Query("limit") limit: Int = 30,
        @Header("Authorization") authorization: String,
    ): List<ConversationSummary>

    @GET("api/v1/chat/conversations/{id}")
    suspend fun getConversation(
        @Path("id") conversationId: String,
        @Header("Authorization") authorization: String,
    ): ConversationDetail

    // -- Memory --
    @GET("api/v1/memory")
    suspend fun listMemories(
        @Header("Authorization") authorization: String,
    ): List<MemoryResponse>

    @POST("api/v1/memory")
    suspend fun createMemory(
        @Body request: MemoryRequest,
        @Header("Authorization") authorization: String,
    ): MemoryResponse

    @DELETE("api/v1/memory/{id}")
    suspend fun deleteMemory(
        @Path("id") memoryId: String,
        @Header("Authorization") authorization: String,
    ): Map<String, String>

    @POST("api/v1/memory/recall")
    suspend fun recallMemory(
        @Body request: MemoryRecallRequest,
        @Header("Authorization") authorization: String,
    ): List<MemoryResponse>

    @GET("api/v1/memory/graph")
    suspend fun memoryGraph(
        @Header("Authorization") authorization: String,
    ): GraphResponse

    @POST("api/v1/memory/{id}/link")
    suspend fun linkMemory(
        @Path("id") sourceId: String,
        @Body request: LinkRequest,
        @Header("Authorization") authorization: String,
    ): Map<String, String>

    // -- Schedule --
    @GET("api/v1/schedule")
    suspend fun listSchedule(
        @Header("Authorization") authorization: String,
    ): List<ScheduleResponse>

    @POST("api/v1/schedule")
    suspend fun createSchedule(
        @Body request: ScheduleRequest,
        @Header("Authorization") authorization: String,
    ): ScheduleResponse

    @DELETE("api/v1/schedule/{id}")
    suspend fun deleteSchedule(
        @Path("id") scheduleId: String,
        @Header("Authorization") authorization: String,
    ): Map<String, String>

    // -- Voice --
    @GET("api/v1/voice/status")
    suspend fun voiceStatus(
        @Header("Authorization") authorization: String,
    ): VoiceStatus

    @POST("api/v1/voice/speak")
    suspend fun speak(
        @Body request: SpeakRequest,
        @Header("Authorization") authorization: String,
    ): Map<String, String>

    // -- Actions --
    @GET("api/v1/actions")
    suspend fun listActions(
        @Header("Authorization") authorization: String,
    ): List<ActionItem>

    @POST("api/v1/actions/dispatch")
    suspend fun dispatchAction(
        @Body request: ActionDispatchRequest,
        @Header("Authorization") authorization: String,
    ): ActionResponse

    // -- Connectors --
    @GET("api/v1/connectors")
    suspend fun listConnectors(
        @Header("Authorization") authorization: String,
    ): List<ConnectorResponse>

    @POST("api/v1/connectors")
    suspend fun createConnector(
        @Body request: ConnectorRequest,
        @Header("Authorization") authorization: String,
    ): ConnectorResponse

    @POST("api/v1/connectors/{name}/call")
    suspend fun callConnector(
        @Path("name") name: String,
        @Body request: ConnectorCallRequest,
        @Header("Authorization") authorization: String,
    ): ConnectorCallResponse
}
