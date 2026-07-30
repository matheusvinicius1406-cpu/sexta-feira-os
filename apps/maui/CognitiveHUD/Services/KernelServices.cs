using System.Diagnostics;

namespace SextaFeira.CognitiveHUD.Services;

// ── KernelConfiguration ───────────────────────────────────

/// <summary>Read-only snapshot of kernel configuration.</summary>
public record KernelConfiguration(
    string Environment,
    string LogLevel,
    string BrainModel,
    string EmbeddingModel,
    string OllamaEndpoint,
    string DatabaseUrl,
    int GrpcPort,
    bool VoiceEnabled,
    bool SchedulerEnabled,
    bool SubagentsEnabled,
    string? ObsidianVault);

// ── KernelState ───────────────────────────────────────────

/// <summary>Observable kernel state.</summary>
public record KernelStateInfo(
    string Status,
    double? StartedAt,
    double UptimeSeconds,
    int MemoryCount,
    int PluginCount,
    string? Error);

/// <summary>Manages kernel lifecycle state transitions.</summary>
public class KernelStateManager
{
    private KernelStateInfo _state = new("stopped", null, 0, 0, 0, null);

    public KernelStateInfo State => _state;

    public void SetStarting()
    {
        _state = _state with { Status = "starting", StartedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds() };
        Debug.WriteLine("[KernelState] starting...");
    }

    public void SetRunning()
    {
        _state = _state with { Status = "running" };
        Debug.WriteLine("[KernelState] running");
    }

    public void SetStopped()
    {
        _state = _state with { Status = "stopped" };
        Debug.WriteLine("[KernelState] stopped");
    }

    public void SetError(string error)
    {
        _state = _state with { Status = "error", Error = error };
        Debug.WriteLine($"[KernelState] error: {error}");
    }

    public void UpdateUptime()
    {
        if (_state.StartedAt.HasValue)
        {
            var uptime = DateTimeOffset.UtcNow.ToUnixTimeSeconds() - _state.StartedAt.Value;
            _state = _state with { UptimeSeconds = uptime };
        }
    }
}

// ── KernelHealth ──────────────────────────────────────────

/// <summary>Aggregated health report.</summary>
public record HealthReport(
    string Status,
    Dictionary<string, bool> Components,
    double UptimeSeconds,
    double MemoryUsageMb);

/// <summary>Aggregates health from registered engines.</summary>
public class KernelHealthService
{
    private readonly Dictionary<string, Func<Task<bool>>> _checks = new();

    public void RegisterCheck(string name, Func<Task<bool>> check)
    {
        _checks[name] = check;
    }

    public async Task<HealthReport> AggregateAsync()
    {
        var results = new Dictionary<string, bool>();
        foreach (var (name, check) in _checks)
        {
            try { results[name] = await check(); }
            catch { results[name] = false; }
        }

        var status = results.Values.All(v => v) ? "ok"
                   : results.Values.Any(v => v) ? "degraded"
                   : "unhealthy";

        return new HealthReport(status, results, 0, 0);
    }
}

// ── KernelMetrics ─────────────────────────────────────────

/// <summary>Runtime metric snapshot.</summary>
public record KernelMetricsInfo(
    int TotalMemories,
    int TotalEvents,
    int TotalChats,
    int TotalActions,
    double AvgResponseTimeMs,
    int ActivePlugins);

/// <summary>Collects runtime metrics.</summary>
public class KernelMetricsCollector
{
    public KernelMetricsInfo Metrics { get; private set; } = new(0, 0, 0, 0, 0, 0);

    public void IncrementChats()
    {
        Metrics = Metrics with { TotalChats = Metrics.TotalChats + 1 };
    }

    public void IncrementActions()
    {
        Metrics = Metrics with { TotalActions = Metrics.TotalActions + 1 };
    }

    public void RecordMemory(int count)
    {
        Metrics = Metrics with { TotalMemories = count };
    }
}

// ── KernelDiagnostics ─────────────────────────────────────

/// <summary>Diagnostic utilities.</summary>
public class KernelDiagnostics
{
    private readonly HashSet<string> _diagnosed = new();

    public void RegisterDiagnostic(string engineName) => _diagnosed.Add(engineName);

    public Dictionary<string, object> RunChecks()
    {
        return new Dictionary<string, object>
        {
            ["diagnosed_engines"] = string.Join(", ", _diagnosed),
            ["timestamp"] = DateTime.UtcNow.ToString("O"),
        };
    }
}
