using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// KernelService — manages kernel lifecycle, health, and aggregated state.
/// Mirrors the Python Kernel class in app/core/di.py.
/// </summary>
public class KernelService
{
    private readonly GrpcClient _grpc;
    private readonly IEventBus _eventBus;

    public KernelService(GrpcClient grpc, IEventBus eventBus)
    {
        _grpc = grpc;
        _eventBus = eventBus;
    }

    /// <summary>
    /// Result of the most recent health probe.
    ///
    /// Deliberately a cached flag rather than a live call: callers such as
    /// the diagnostics panel read it from synchronous binding code, where
    /// awaiting is not an option. It is false until the first probe runs.
    /// </summary>
    public bool IsReady { get; private set; }

    /// <summary>Check if the backend kernel is alive.</summary>
    public async Task<bool> IsAliveAsync()
    {
        IsReady = await _grpc.CheckHealthCoreAsync() is not null;
        return IsReady;
    }

    /// <summary>Get full health status.</summary>
    public async Task<HealthStatus> GetHealthAsync()
    {
        var pb = await _grpc.CheckHealthCoreAsync();
        IsReady = pb is not null;
        return new HealthStatus(
            IsOnline: pb is not null,
            Status: pb?.Status ?? "offline",
            Version: pb?.Version ?? "unknown",
            OllamaOnline: pb?.OllamaOnline ?? false,
            VoiceAvailable: pb?.VoiceAvailable ?? false,
            UptimeSeconds: pb?.UptimeSeconds ?? 0);
    }
}
