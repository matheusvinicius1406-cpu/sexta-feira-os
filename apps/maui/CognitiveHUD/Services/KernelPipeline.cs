using System.Diagnostics;

namespace SextaFeira.CognitiveHUD.Services;

// ── PipelineStep ─────────────────────────────────────────

/// <summary>A single step in the startup pipeline.</summary>
public record PipelineStep(
    string Name,
    int Order,
    Func<Task> Handler,
    TimeSpan Timeout,
    bool Critical = true);

// ── StartupPipeline ──────────────────────────────────────

/// <summary>Orchestrated kernel startup with observable progress.</summary>
public class StartupPipeline
{
    private readonly List<PipelineStep> _steps = new();
    private readonly IEventBus _eventBus;
    private int _currentStep;
    private readonly List<string> _errors = new();

    public StartupPipeline(IEventBus eventBus) => _eventBus = eventBus;

    public void AddStep(PipelineStep step) => _steps.Add(step);

    public double Progress => _steps.Count > 0 ? (double)_currentStep / _steps.Count : 1.0;

    public IReadOnlyList<string> Errors => _errors.AsReadOnly();

    public async Task<bool> RunAsync()
    {
        _errors.Clear();
        _currentStep = 0;
        await _eventBus.PublishAsync("kernel.started", new Dictionary<string, object>());

        var ordered = _steps.OrderBy(s => s.Order).ToList();

        foreach (var step in ordered)
        {
            _currentStep = step.Order;
            Debug.WriteLine($"[Pipeline] {step.Name}...");

            try
            {
                using var cts = new CancellationTokenSource(step.Timeout);
                await step.Handler().WaitAsync(cts.Token);
                await _eventBus.PublishAsync("pipeline.step_completed",
                    new Dictionary<string, object> { ["step"] = step.Name });
            }
            catch (OperationCanceledException)
            {
                var msg = $"Step '{step.Name}' timed out";
                Debug.WriteLine($"[Pipeline] {msg}");
                if (step.Critical) { _errors.Add(msg); return false; }
            }
            catch (Exception ex)
            {
                var msg = $"Step '{step.Name}' failed: {ex.Message}";
                Debug.WriteLine($"[Pipeline] {msg}");
                if (step.Critical) { _errors.Add(msg); return false; }
            }
        }

        await _eventBus.PublishAsync("kernel.ready", new Dictionary<string, object>());
        Debug.WriteLine("[Pipeline] Kernel ready");
        return true;
    }
}

// ── ShutdownTask ─────────────────────────────────────────

/// <summary>A single task in the shutdown pipeline.</summary>
public record ShutdownTask(
    string Name,
    int Order,
    Func<Task> Handler,
    TimeSpan Timeout);

// ── ShutdownPipeline ─────────────────────────────────────

/// <summary>Graceful kernel shutdown with state saving.</summary>
public class ShutdownPipeline
{
    private readonly List<ShutdownTask> _tasks = new();
    private readonly IEventBus _eventBus;
    private readonly List<string> _saved = new();

    public ShutdownPipeline(IEventBus eventBus) => _eventBus = eventBus;

    public void AddTask(ShutdownTask task) => _tasks.Add(task);

    public IReadOnlyList<string> Saved => _saved.AsReadOnly();

    public async Task RunAsync()
    {
        _saved.Clear();
        Debug.WriteLine("[Shutdown] Starting graceful shutdown...");
        await _eventBus.PublishAsync("kernel.shutdown", new Dictionary<string, object>());

        foreach (var task in _tasks.OrderByDescending(t => t.Order))
        {
            Debug.WriteLine($"[Shutdown] {task.Name}...");
            try
            {
                using var cts = new CancellationTokenSource(task.Timeout);
                await task.Handler().WaitAsync(cts.Token);
                _saved.Add(task.Name);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[Shutdown] {task.Name} failed: {ex.Message}");
            }
        }

        Debug.WriteLine($"[Shutdown] Complete. Saved: {string.Join(", ", _saved)}");
    }
}

// ── HealthCheck / HealthMonitor ──────────────────────────

/// <summary>A single health check.</summary>
public record HealthCheckDef(
    string Name,
    Func<Task<bool>> Check,
    TimeSpan Interval,
    TimeSpan Timeout,
    bool Critical = false);

/// <summary>Health snapshot.</summary>
public record HealthSnapshot(
    DateTime Timestamp,
    string Status,
    Dictionary<string, bool> Checks,
    double UptimeSeconds,
    double MemoryMb,
    double LatencyMs);

/// <summary>Periodic health monitoring.</summary>
public class HealthMonitor
{
    private readonly List<HealthCheckDef> _checks = new();
    private readonly IEventBus _eventBus;
    private CancellationTokenSource? _cts;
    private HealthSnapshot? _lastSnapshot;

    public HealthMonitor(IEventBus eventBus) => _eventBus = eventBus;

    public HealthSnapshot? LastSnapshot => _lastSnapshot;
    public bool IsRunning => _cts is not null && !_cts.IsCancellationRequested;

    public void Register(HealthCheckDef check) => _checks.Add(check);

    public async Task<HealthSnapshot> SnapshotAsync()
    {
        var start = DateTime.UtcNow;
        var results = new Dictionary<string, bool>();

        foreach (var hc in _checks)
        {
            try
            {
                using var cts = new CancellationTokenSource(hc.Timeout);
                results[hc.Name] = await hc.Check().WaitAsync(cts.Token);
            }
            catch { results[hc.Name] = false; }
        }

        var status = results.Values.Any(v => !v) ? "degraded" : "ok";
        if (results.Values.All(v => !v)) status = "unhealthy";

        _lastSnapshot = new HealthSnapshot(
            DateTime.UtcNow, status, results, 0, 0,
            (DateTime.UtcNow - start).TotalMilliseconds);
        return _lastSnapshot;
    }

    public async Task StartAsync(TimeSpan? interval = null)
    {
        _cts = new CancellationTokenSource();
        var intervalValue = interval ?? TimeSpan.FromSeconds(30);

        try
        {
            while (!_cts.Token.IsCancellationRequested)
            {
                await Task.Delay(intervalValue, _cts.Token);
                await SnapshotAsync();
            }
        }
        catch (OperationCanceledException) { }
    }

    public void Stop()
    {
        _cts?.Cancel();
    }
}
