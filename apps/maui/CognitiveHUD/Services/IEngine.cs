namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Engine contract — each cognitive engine must implement this.
/// Mirrors Python's IEngine interface exactly.
/// </summary>
public interface IEngine
{
    /// <summary>Unique engine name (e.g. "Memory", "Cognition").</summary>
    string Name { get; }

    /// <summary>Initialize the engine (async setup, loading models, etc.).</summary>
    Task InitializeAsync();

    /// <summary>Health check — returns true if the engine is operational.</summary>
    Task<bool> HealthAsync();

    /// <summary>Graceful shutdown — release resources.</summary>
    Task ShutdownAsync();
}
