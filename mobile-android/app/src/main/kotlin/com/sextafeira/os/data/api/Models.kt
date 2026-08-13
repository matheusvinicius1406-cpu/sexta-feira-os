package com.sextafeira.os.data.api

import com.google.gson.annotations.SerializedName

// ── Auth ────────────────────────────────────────────────

data class LoginRequest(
    val email: String,
    val password: String,
)

data class TokenResponse(
    @field:SerializedName("access_token") val accessToken: String,
    @field:SerializedName("token_type") val tokenType: String = "bearer",
    @field:SerializedName("owner_id") val ownerId: String,
)

data class PairRequest(
    @field:SerializedName("pairing_code") val pairingCode: String,
    @field:SerializedName("device_name") val deviceName: String,
    @field:SerializedName("device_kind") val deviceKind: String = "phone",
)

data class PairResponse(
    @field:SerializedName("device_token") val deviceToken: String,
    @field:SerializedName("device_id") val deviceId: String,
)

// ── Chat ────────────────────────────────────────────────

data class ChatRequest(
    val message: String,
    @field:SerializedName("conversation_id") val conversationId: String? = null,
    @field:SerializedName("device_id") val deviceId: String? = null,
)

data class ChatResponse(
    val reply: String,
    @field:SerializedName("conversation_id") val conversationId: String,
)

// ── SSE stream events ──────────────────────────────────

data class StreamChunk(
    val chunk: String? = null,
    @field:SerializedName("conversation_id") val conversationId: String? = null,
    val done: Boolean? = null,
    val error: String? = null,
)

// ── Conversations ───────────────────────────────────────

data class ConversationSummary(
    val id: String,
    val title: String? = null,
    @field:SerializedName("updated_at") val updatedAt: String? = null,
    @field:SerializedName("message_count") val messageCount: Int = 0,
)

data class ConversationDetail(
    val id: String,
    val title: String? = null,
    val messages: List<MessageItem> = emptyList(),
)

data class MessageItem(
    val role: String,
    val content: String,
    @field:SerializedName("created_at") val createdAt: String? = null,
)

// ── Health ──────────────────────────────────────────────

data class HealthResponse(
    val status: String,
    val app: String? = null,
    val version: String? = null,
    @field:SerializedName("brain_online") val brainOnline: Boolean = false,
    @field:SerializedName("brain_model") val brainModel: String? = null,
    @field:SerializedName("access_mode") val accessMode: String? = null,
    val timestamp: String? = null,
)

// ── Obsidian ────────────────────────────────────────────

data class ObsidianStatus(
    @field:SerializedName("vault_path") val vaultPath: String? = null,
    @field:SerializedName("vault_exists") val vaultExists: Boolean = false,
    @field:SerializedName("notes_count") val notesCount: Int = 0,
    @field:SerializedName("watcher_running") val watcherRunning: Boolean = false,
)

// ── Device ──────────────────────────────────────────────

data class DeviceInfo(
    val id: String,
    val name: String,
    val kind: String,
    @field:SerializedName("paired_at") val pairedAt: String? = null,
    @field:SerializedName("last_seen_at") val lastSeenAt: String? = null,
    val revoked: Boolean = false,
)

// ── Memory ──────────────────────────────────────────────

/** Full memory node as returned by GET /api/v1/memory (list) and POST /recall. */
data class MemoryItem(
    val id: String,
    val title: String? = null,
    val content: String? = null,
    val kind: String = "fact",
    val importance: Double = 0.5,
    val source: String? = null,
    @field:SerializedName("created_at") val createdAt: String? = null,
    val similarity: Double? = null,
)

/** Request body for POST /api/v1/memory (teach the kernel a new fact). */
data class TeachRequest(
    val content: String,
    val title: String? = null,
    val kind: String = "fact",
    val importance: Double = 0.5,
)

/** Request body for POST /api/v1/memory/recall (search). */
data class RecallRequest(
    val query: String,
    val networked: Boolean = true,
    @field:SerializedName("top_k") val topK: Int? = null,
)

/** Full graph response from GET /api/v1/memory/graph. */
data class GraphResponse(
    val nodes: List<GraphNode> = emptyList(),
    val edges: List<GraphEdge> = emptyList(),
)

data class GraphNode(
    val id: String,
    val title: String? = null,
    val kind: String = "fact",
    val importance: Double = 0.5,
)

data class GraphEdge(
    val source: String,
    val target: String,
    val relation: String = "related",
    val weight: Double = 1.0,
)

/** Response from DELETE /api/v1/memory/{id}. */
data class ForgetResponse(
    val forgotten: String,
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

// ── Voice ──────────────────────────────────────────────

/** Request body for POST /api/v1/voice/speak. */
data class SpeakRequest(
    val text: String,
)

data class VoiceStatusResponse(
    val enabled: Boolean = false,
    @field:SerializedName("stt_available") val sttAvailable: Boolean = false,
    @field:SerializedName("tts_available") val ttsAvailable: Boolean = false,
)

data class TranscribeResponse(
    val text: String,
)

/** Response from POST /api/v1/voice/chat (full voice loop). */
data class VoiceChatResponse(
    val transcript: String,
    val reply: String,
    @field:SerializedName("conversation_id") val conversationId: String,
    @field:SerializedName("audio_wav_base64") val audioWavBase64: String? = null,
)

// ── Security (self-defense dashboard) ───────────────────

data class SecurityAuditResponse(
    @field:SerializedName("auditado_em") val auditedAt: String? = null,
    @field:SerializedName("acesso") val access: SecurityAccess? = null,
    @field:SerializedName("defesas") val defenses: SecurityDefenses? = null,
    @field:SerializedName("ameacas") val threats: SecurityThreatSummary? = null,
    @field:SerializedName("recomendacoes") val recommendations: List<String> = emptyList(),
)

data class SecurityAccess(
    @field:SerializedName("access_mode") val accessMode: String? = null,
    @field:SerializedName("auth_dev_bypass") val authDevBypass: Boolean = false,
)

data class SecurityDefenses(
    val headers: List<String> = emptyList(),
    @field:SerializedName("rate_limit") val rateLimit: SecurityRateLimit? = null,
    val netguard: SecurityNetguard? = null,
    @field:SerializedName("honeypots_armados") val honeypotsArmed: Int = 0,
)

data class SecurityRateLimit(
    @field:SerializedName("max_tentativas") val maxAttempts: Int = 0,
    @field:SerializedName("lockout_segundos") val lockoutSeconds: Int = 0,
    @field:SerializedName("ips_bloqueados_agora") val lockedIpsNow: Int = 0,
)

data class SecurityNetguard(
    val ativo: Boolean = false,
    @field:SerializedName("hosts_internos_permitidos") val allowedHosts: List<String> = emptyList(),
)

data class SecurityThreatSummary(
    val total: Int = 0,
    val recentes: List<SecurityThreat> = emptyList(),
)

data class SecurityThreat(
    val id: String? = null,
    val type: String? = null,
    val detail: String? = null,
    @field:SerializedName("source_ip") val sourceIp: String? = null,
    val at: String? = null,
    val sequence: Int = 0,
)

// ── Generic Error ───────────────────────────────────────

data class ErrorResponse(
    val detail: String? = null,
)
