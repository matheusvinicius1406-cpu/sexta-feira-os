using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Cognition service contract — mirrors Python CognitionAdapter.
/// Manages chat, health checks, and brain state.
/// </summary>
public interface ICognitionService
{
    /// <summary>Check if the backend brain is healthy and online.</summary>
    Task<HealthStatus> CheckHealthAsync();

    /// <summary>Stream chat tokens for a user message.</summary>
    IAsyncEnumerable<string> ChatStreamAsync(string message, string? conversationId = null);

    /// <summary>Send a chat message and get the full reply (non-streaming convenience).</summary>
    Task<string> ChatAsync(string message, string? conversationId = null);
}
