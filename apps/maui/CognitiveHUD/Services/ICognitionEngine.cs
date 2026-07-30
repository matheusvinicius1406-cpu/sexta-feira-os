using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Cognition Engine contract — mirrors Python CognitionEngine.
/// Manages chat streams, health checks, and brain state.
/// </summary>
public interface ICognitionEngine : IEngine
{
    Task<HealthStatus> CheckHealthAsync();
    IAsyncEnumerable<string> ChatStreamAsync(string message, string? conversationId = null);
    Task<string> ChatAsync(string message, string? conversationId = null);
}
