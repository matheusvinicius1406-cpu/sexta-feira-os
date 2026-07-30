using System.Reflection;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// PluginLoader — discovers and loads plugins from assemblies.
/// Mirrors Python PluginLoader in backend-core/app/plugins/loader.py.
/// </summary>
public class PluginLoader
{
    private readonly PluginRegistry _registry;

    public PluginLoader(PluginRegistry registry)
    {
        _registry = registry;
    }

    /// <summary>Scan an assembly for IPlugin implementations and register them.</summary>
    public int LoadFromAssembly(Assembly assembly)
    {
        var count = 0;
        var pluginType = typeof(IPlugin);
        var baseType = typeof(PluginBase);

        var types = assembly.GetTypes()
            .Where(t => t is { IsClass: true, IsAbstract: false }
                        && pluginType.IsAssignableFrom(t)
                        && t != baseType);

        foreach (var type in types)
        {
            try
            {
                if (Activator.CreateInstance(type) is IPlugin instance)
                {
                    _registry.Register(instance);
                    count++;
                    System.Diagnostics.Debug.WriteLine($"Loaded plugin: {instance.PluginId} ({type.Name})");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to load plugin {type.Name}: {ex.Message}");
            }
        }

        return count;
    }

    /// <summary>Scan the current app domain assemblies for plugins.</summary>
    public int LoadAll()
    {
        var count = 0;
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            try { count += LoadFromAssembly(asm); }
            catch { /* skip assemblies that can't be scanned */ }
        }
        return count;
    }
}
