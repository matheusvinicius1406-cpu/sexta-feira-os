namespace SextaFeira.CognitiveHUD.Models;

/// <summary>A single chat message (sent by user or received from AI).</summary>
public record ChatMessage(
    string Id,
    string Role,       // "user" | "assistant" | "system"
    string Content,
    DateTime Timestamp,
    bool IsStreaming = false);

/// <summary>Result of a health check against the cognition engine.</summary>
public record HealthStatus(
    bool IsOnline,
    string Status,
    string Version,
    bool OllamaOnline,
    bool VoiceAvailable,
    int UptimeSeconds);

/// <summary>Conversation state for tracking multi-turn chat.</summary>
public record Conversation(
    string Id,
    string Title,
    DateTime CreatedAt,
    int MessageCount);
