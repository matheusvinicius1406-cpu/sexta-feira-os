namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Default engine stub — used as a safe placeholder for engines that
/// don't have a real C# implementation yet (Planning, Learning, etc.).
/// Prevents NullReferenceException when injected into ViewModels.
///
/// Deliberately not sealed: the per-domain stubs in EngineStubs.cs derive
/// from it to pick up this behaviour while satisfying their own marker
/// interfaces. Members are virtual so a real implementation can replace
/// them one at a time instead of all at once.
/// </summary>
public class DefaultEngine : IEngine
{
    public string Name { get; }

    public DefaultEngine(string name)
    {
        Name = name;
    }

    public virtual Task InitializeAsync()
    {
        System.Diagnostics.Debug.WriteLine($"[{Name}Engine] Initialized (placeholder)");
        return Task.CompletedTask;
    }

    public virtual Task<bool> HealthAsync()
    {
        return Task.FromResult(false); // offline until real implementation
    }

    public virtual Task ShutdownAsync()
    {
        System.Diagnostics.Debug.WriteLine($"[{Name}Engine] Shutdown (placeholder)");
        return Task.CompletedTask;
    }
}
