package com.sextafeira.os.data.api

import com.google.gson.annotations.SerializedName

// ── Auth ────────────────────────────────────────────────

data class LoginRequest(
    val email: String,
    val password: String,
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer",
    @SerializedName("owner_id") val ownerId: String,
)

data class PairRequest(
    @SerializedName("pairing_code") val pairingCode: String,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("device_kind") val deviceKind: String = "phone",
)

data class PairResponse(
    @SerializedName("device_token") val deviceToken: String,
    @SerializedName("device_id") val deviceId: String,
)

// ── Chat ────────────────────────────────────────────────

data class ChatRequest(
    val message: String,
    @SerializedName("conversation_id") val conversationId: String? = null,
    @SerializedName("device_id") val deviceId: String? = null,
)

data class ChatResponse(
    val reply: String,
    @SerializedName("conversation_id") val conversationId: String,
)

// ── SSE stream events ──────────────────────────────────

data class StreamChunk(
    val chunk: String? = null,
    @SerializedName("conversation_id") val conversationId: String? = null,
    val done: Boolean? = null,
    val error: String? = null,
)

// ── Conversations ───────────────────────────────────────

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

// ── Health ──────────────────────────────────────────────

data class HealthResponse(
    val status: String,
    val app: String? = null,
    val version: String? = null,
    @SerializedName("brain_online") val brainOnline: Boolean = false,
    @SerializedName("brain_model") val brainModel: String? = null,
    @SerializedName("access_mode") val accessMode: String? = null,
    val timestamp: String? = null,
)

// ── Obsidian ────────────────────────────────────────────

data class ObsidianStatus(
    @SerializedName("vault_path") val vaultPath: String? = null,
    @SerializedName("vault_exists") val vaultExists: Boolean = false,
    @SerializedName("notes_count") val notesCount: Int = 0,
    @SerializedName("watcher_running") val watcherRunning: Boolean = false,
)

// ── Device ──────────────────────────────────────────────

data class DeviceInfo(
    val id: String,
    val name: String,
    val kind: String,
    @SerializedName("paired_at") val pairedAt: String? = null,
    @SerializedName("last_seen_at") val lastSeenAt: String? = null,
    val revoked: Boolean = false,
)

// ── Memory ──────────────────────────────────────────────

data class MemoryItem(
    val id: String,
    val title: String? = null,
    val content: String? = null,
    val similarity: Double? = null,
)

// ── Reminders ───────────────────────────────────────────

data class ReminderRequest(
    val title: String,
    val datetime: String,
    val recurring: String? = null,
)

data class ReminderResponse(
    val id: String,
    val title: String,
    val datetime: String,
    val recurring: String? = null,
    val fired: Boolean = false,
)

// ── Connector ───────────────────────────────────────────

data class ConnectorInfo(
    val id: String,
    val name: String,
    val description: String? = null,
    val enabled: Boolean = false,
)

// ── Generic Error ───────────────────────────────────────

data class ErrorResponse(
    val detail: String? = null,
)
