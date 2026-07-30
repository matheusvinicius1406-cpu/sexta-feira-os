namespace SextaFeira.CognitiveHUD.Services;

// ── PluginManifest ────────────────────────────────────────

/// <summary>Declarative metadata for a plugin package.</summary>
public record PluginManifest(
    string PluginId,
    string DisplayName,
    string Version = "1.0.0",
    string Author = "",
    string Description = "",
    IReadOnlyList<string>? Dependencies = null,
    IReadOnlyList<string>? Permissions = null,
    string MinKernelVersion = "1.0.0",
    string EntryPoint = "");

// ── PluginPermissions ─────────────────────────────────────

/// <summary>Runtime permission check for plugins.</summary>
public static class PluginPermissions
{
    private static readonly HashSet<string> _granted = new();

    public static void Require(params string[] permissions)
    {
        foreach (var p in permissions)
            if (!_granted.Contains(p))
                throw new UnauthorizedAccessException($"Plugin missing permission: {p}");
    }

    public static void Grant(string pluginId, params string[] permissions)
    {
        foreach (var p in permissions)
            _granted.Add($"{pluginId}:{p}");
    }

    public static void Revoke(string pluginId, params string[] permissions)
    {
        foreach (var p in permissions)
            _granted.Remove($"{pluginId}:{p}");
    }

    public static void Clear() => _granted.Clear();
}

// ── PluginSandbox ─────────────────────────────────────────

/// <summary>Executes plugin code in isolation (basic implementation).</summary>
public class PluginSandbox
{
    private readonly string _pluginId;

    public PluginSandbox(string pluginId) => _pluginId = pluginId;

    public Task<object?> ExecuteAsync(string code, Dictionary<string, object?>? context = null)
    {
        try
        {
            // In a real implementation, this would use AppDomain isolation
            System.Diagnostics.Debug.WriteLine($"[Sandbox] {_pluginId}: executing code");
            return Task.FromResult<object?>(null);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Sandbox] Error in {_pluginId}: {ex.Message}");
            throw;
        }
    }
}

// ── PluginLifecycle ───────────────────────────────────────

/// <summary>Plugin lifecycle state machine.</summary>
public enum PluginState
{
    Unloaded,
    Loaded,
    Enabled,
    Running,
    Error,
}

/// <summary>Manages plugin state transitions.</summary>
public class PluginLifecycle
{
    private readonly Dictionary<string, PluginState> _states = new();

    public PluginState GetState(string pluginId) =>
        _states.GetValueOrDefault(pluginId, PluginState.Unloaded);

    public bool CanTransition(string pluginId, PluginState toState)
    {
        var current = GetState(pluginId);
        return toState switch
        {
            PluginState.Loaded => current == PluginState.Unloaded,
            PluginState.Enabled => current == PluginState.Loaded,
            PluginState.Running => current == PluginState.Enabled,
            PluginState.Error => current is PluginState.Loaded or PluginState.Enabled or PluginState.Running,
            PluginState.Unloaded => current == PluginState.Loaded || current == PluginState.Error,
            _ => false,
        };
    }

    public void Transition(string pluginId, PluginState toState)
    {
        if (!CanTransition(pluginId, toState))
            throw new InvalidOperationException(
                $"Cannot transition plugin '{pluginId}' from '{GetState(pluginId)}' to '{toState}'");
        _states[pluginId] = toState;
        System.Diagnostics.Debug.WriteLine($"[PluginLifecycle] {pluginId} => {toState}");
    }
}

// ── PluginHotReload ───────────────────────────────────────

/// <summary>Monitors plugin files for changes and reloads them.</summary>
public class PluginHotReload
{
    private readonly PluginRegistry _registry;
    private readonly Dictionary<string, string> _checksums = new();
    private readonly Dictionary<string, DateTime> _lastWriteTimes = new();

    public PluginHotReload(PluginRegistry registry) => _registry = registry;

    public IReadOnlyList<string> CheckAndReload(string directoryPath)
    {
        var reloaded = new List<string>();
        if (!Directory.Exists(directoryPath))
            return reloaded.AsReadOnly();

        foreach (var file in Directory.GetFiles(directoryPath, "*.dll", SearchOption.AllDirectories))
        {
            var lastWrite = File.GetLastWriteTimeUtc(file);
            if (_lastWriteTimes.TryGetValue(file, out var cached) && cached >= lastWrite)
                continue;
            _lastWriteTimes[file] = lastWrite;
            System.Diagnostics.Debug.WriteLine($"[HotReload] Detected change: {file}");
            reloaded.Add(Path.GetFileNameWithoutExtension(file));
        }

        return reloaded.AsReadOnly();
    }
}

// ── PluginDependencyResolver ──────────────────────────────

/// <summary>Resolves plugin dependencies using topological sort.</summary>
public class PluginDependencyResolver
{
    public IReadOnlyList<string> Resolve(IReadOnlyList<PluginManifest> manifests)
    {
        var graph = manifests.ToDictionary(m => m.PluginId, m => m.Dependencies?.ToList() ?? new List<string>());
        var resolved = new List<string>();
        var visited = new HashSet<string>();

        void Visit(string pid, HashSet<string> path)
        {
            if (path.Contains(pid))
                throw new InvalidOperationException($"Circular dependency detected: {pid}");
            if (visited.Contains(pid))
                return;
            path.Add(pid);
            if (graph.TryGetValue(pid, out var deps))
            {
                foreach (var dep in deps)
                    if (graph.ContainsKey(dep))
                        Visit(dep, path);
            }
            path.Remove(pid);
            visited.Add(pid);
            resolved.Add(pid);
        }

        foreach (var pid in graph.Keys)
            if (!visited.Contains(pid))
                Visit(pid, new HashSet<string>());

        return resolved.AsReadOnly();
    }
}
