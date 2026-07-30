using System.Collections.Generic;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Central registry for discovering and managing plugins.
/// Mirrors Python PluginRegistry in backend-core/app/plugins/__init__.py exactly.
/// </summary>
public class PluginRegistry
{
    private readonly Dictionary<string, IPlugin> _plugins = new();

    /// <summary>Register a plugin by its PluginId.</summary>
    public void Register(IPlugin plugin)
    {
        var pid = plugin.PluginId;
        if (_plugins.ContainsKey(pid))
            throw new InvalidOperationException($"Plugin '{pid}' is already registered");
        _plugins[pid] = plugin;
    }

    /// <summary>Retrieve a registered plugin by ID, or null if not found.</summary>
    public IPlugin? Get(string pluginId)
    {
        return _plugins.TryGetValue(pluginId, out var plugin) ? plugin : null;
    }

    /// <summary>All registered plugins (read-only snapshot).</summary>
    public IReadOnlyDictionary<string, IPlugin> All => new Dictionary<string, IPlugin>(_plugins);

    /// <summary>Number of registered plugins.</summary>
    public int Count => _plugins.Count;

    /// <summary>Initialize every registered plugin.</summary>
    public async Task InitializeAllAsync()
    {
        foreach (var kvp in _plugins)
        {
            try
            {
                await kvp.Value.InitializeAsync();
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException($"Plugin '{kvp.Key}' failed to initialize: {ex.Message}", ex);
            }
        }
    }
}
