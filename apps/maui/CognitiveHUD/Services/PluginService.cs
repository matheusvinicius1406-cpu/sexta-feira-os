namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// PluginService — facade over PluginRegistry, PluginLoader, and PluginDiscovery.
/// </summary>
public class PluginService
{
    private readonly PluginRegistry _registry;
    private readonly PluginLoader _loader;
    private readonly PluginDiscovery _discovery;

    public PluginService(PluginRegistry registry, PluginLoader loader, PluginDiscovery discovery)
    {
        _registry = registry;
        _loader = loader;
        _discovery = discovery;
    }

    public PluginRegistry Registry => _registry;
    public PluginLoader Loader => _loader;
    public PluginDiscovery Discovery => _discovery;

    public int LoadAll() => _loader.LoadAll();

    public IReadOnlyList<PluginManifest> ListCapabilities() => _discovery.ListCapabilities();

    public IPlugin? GetPlugin(string pluginId) => _registry.Get(pluginId);

    public int Count => _registry.Count;
}
