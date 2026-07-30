namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Default engine stub — used as a safe placeholder for engines that
/// don't have a real C# implementation yet (Planning, Learning, etc.).
/// Prevents NullReferenceException when injected into ViewModels.
/// </summary>
public sealed class DefaultEngine : IEngine
{
    public string Name { get; }

    public DefaultEngine(string name)
    {
        Name = name;
    }

    public Task InitializeAsync()
    {
        System.Diagnostics.Debug.WriteLine($"[{Name}Engine] Initialized (placeholder)");
        return Task.CompletedTask;
    }

    public Task<bool> HealthAsync()
    {
        return Task.FromResult(false); // offline until real implementation
    }

    public Task ShutdownAsync()
    {
        System.Diagnostics.Debug.WriteLine($"[{Name}Engine] Shutdown (placeholder)");
        return Task.CompletedTask;
    }
}
