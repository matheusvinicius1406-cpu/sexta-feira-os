namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Application-level startup pipeline — mirrors Python StartupPipeline.
/// Orchestrates initialization steps: config → theme → DI → gRPC → bus → plugins → HUD → ready.
/// </summary>
public class MauiStartupPipeline
{
    private readonly List<BaseStep> _steps;
    private int _currentIndex;
    private readonly List<string> _errors = new();

    public static readonly IReadOnlyList<Type> DefaultStepTypes = new List<Type>
    {
        typeof(ConfigurationStep),
        typeof(ThemeStep),
        typeof(DIContainerStep),
        typeof(GrpcConnectStep),
        typeof(EventBusInitStep),
        typeof(PluginLoadStep),
        typeof(HudInitStep),
        typeof(ReadyStep),
    }.AsReadOnly();

    public MauiStartupPipeline(IReadOnlyList<Type>? stepTypes = null)
    {
        _steps = (stepTypes ?? DefaultStepTypes)
            .Select(t => (BaseStep)Activator.CreateInstance(t)!)
            .ToList();
    }

    public double Progress => _steps.Count > 0 ? (double)(_currentIndex + 1) / _steps.Count : 1.0;
    public IReadOnlyList<string> Errors => _errors.AsReadOnly();
    public string CurrentStepName => _currentIndex < _steps.Count ? _steps[_currentIndex].Name : "done";

    /// <summary>Run all pipeline steps.</summary>
    public async Task<bool> RunAsync(IServiceProvider services)
    {
        _errors.Clear();
        _currentIndex = 0;

        foreach (var step in _steps)
        {
            System.Diagnostics.Debug.WriteLine($"[Pipeline] {step.Name}...");
            try
            {
                using var cts = new CancellationTokenSource(step.Timeout);
                await step.ExecuteAsync(services).WaitAsync(cts.Token);
            }
            catch (OperationCanceledException)
            {
                var msg = $"Step '{step.Name}' timed out after {step.Timeout.TotalSeconds}s";
                System.Diagnostics.Debug.WriteLine($"[Pipeline] {msg}");
                _errors.Add(msg);
                if (step.Critical) return false;
            }
            catch (Exception ex)
            {
                var msg = $"Step '{step.Name}' failed: {ex.Message}";
                System.Diagnostics.Debug.WriteLine($"[Pipeline] {msg}");
                _errors.Add(msg);
                if (step.Critical) return false;
            }
            _currentIndex++;
        }

        System.Diagnostics.Debug.WriteLine("[Pipeline] All steps completed successfully");
        return true;
    }
}
