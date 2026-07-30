namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Plugin contract — each plugin registers capabilities.
/// Mirrors the Python Plugin System contract.
/// </summary>
public interface IPlugin
{
    /// <summary>Unique plugin identifier (e.g. "calendar", "whatsapp").</summary>
    string PluginId { get; }

    /// <summary>Human-readable display name.</summary>
    string DisplayName { get; }

    /// <summary>Initialize the plugin.</summary>
    Task InitializeAsync();

    /// <summary>Execute the plugin's primary action.</summary>
    Task<PluginResult> ExecuteAsync(PluginContext context);

    /// <summary>Get current plugin status.</summary>
    Task<PluginStatus> GetStatusAsync();
}

/// <summary>Context provided when executing a plugin action.</summary>
public record PluginContext(
    string Action,
    Dictionary<string, object> Parameters
);

/// <summary>Result from a plugin execution.</summary>
public record PluginResult(
    bool Success,
    string? Message = null,
    Dictionary<string, object>? Data = null
);

/// <summary>Plugin health status.</summary>
public record PluginStatus(
    bool IsLoaded,
    string? Version = null,
    string? Error = null
);
