namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// PluginDiscovery — runtime discovery of plugin capabilities.
/// Mirrors Python PluginDiscovery in backend-core/app/plugins/discovery.py.
/// </summary>
public class PluginDiscovery
{
    private readonly PluginRegistry _registry;

    public PluginDiscovery(PluginRegistry registry)
    {
        _registry = registry;
    }

    /// <summary>Return a manifest of all registered plugins.</summary>
    public IReadOnlyList<PluginManifest> ListCapabilities()
    {
        // EntryPoint carries the concrete plugin type. It used to land in a
        // second, lightweight PluginManifest declared in this file, which
        // collided with the real one in PluginManifest.cs.
        return _registry.All.Select(kvp => new PluginManifest(
            PluginId: kvp.Value.PluginId,
            DisplayName: kvp.Value.DisplayName,
            EntryPoint: kvp.Value.GetType().Name)).ToList().AsReadOnly();
    }

    /// <summary>Find plugins matching a capability keyword.</summary>
    public IReadOnlyList<IPlugin> Find(string capability)
    {
        var capLower = capability.ToLowerInvariant();
        return _registry.All.Values
            .Where(p => p.PluginId.Contains(capLower) || p.DisplayName.Contains(capLower))
            .ToList().AsReadOnly();
    }

    /// <summary>Execute a plugin action by ID.</summary>
    public async Task<PluginResult?> ExecuteAsync(string pluginId, string action,
        Dictionary<string, object>? parameters = null)
    {
        var plugin = _registry.Get(pluginId);
        if (plugin is null) return null;
        var ctx = new PluginContext(action, parameters ?? new Dictionary<string, object>());
        return await plugin.ExecuteAsync(ctx);
    }
}
