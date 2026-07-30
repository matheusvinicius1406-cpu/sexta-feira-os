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

    /// <summary>Check if the backend kernel is alive.</summary>
    public async Task<bool> IsAliveAsync()
    {
        return await _grpc.CheckHealthCoreAsync() is not null;
    }

    /// <summary>Get full health status.</summary>
    public async Task<HealthStatus> GetHealthAsync()
    {
        var pb = await _grpc.CheckHealthCoreAsync();
        return new HealthStatus(
            IsOnline: pb is not null,
            Status: pb?.Status ?? "offline",
            Version: pb?.Version ?? "unknown",
            OllamaOnline: pb?.OllamaOnline ?? false,
            VoiceAvailable: pb?.VoiceAvailable ?? false,
            UptimeSeconds: pb?.UptimeSeconds ?? 0);
    }
}
