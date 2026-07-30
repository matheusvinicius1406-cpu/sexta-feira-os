namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Convenience base class that plugins can extend.
/// Mirrors Python PluginBase in backend-core/app/plugins/__init__.py exactly.
/// </summary>
public abstract class PluginBase : IPlugin
{
    public virtual string PluginId => GetType().Name.ToLowerInvariant();

    public virtual string DisplayName =>
        string.Join(" ", System.Text.RegularExpressions.Regex
            .Split(GetType().Name, @"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"))
            .Trim();

    public virtual Task InitializeAsync() => Task.CompletedTask;

    public virtual Task<PluginStatus> GetStatusAsync() =>
        Task.FromResult(new PluginStatus(IsLoaded: true, Version: "1.0.0"));

    public abstract Task<PluginResult> ExecuteAsync(PluginContext context);
}
