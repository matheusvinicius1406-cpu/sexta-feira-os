namespace SextaFeira.CognitiveHUD.Services;

// ── BaseStep ─────────────────────────────────────────────

/// <summary>Base class for all pipeline steps.</summary>
public abstract class BaseStep
{
    public abstract string Name { get; }
    public virtual TimeSpan Timeout => TimeSpan.FromSeconds(30);
    public virtual bool Critical => true;
    public abstract Task ExecuteAsync(IServiceProvider services);
}

// ── Concrete Steps ───────────────────────────────────────

public class ConfigurationStep : BaseStep
{
    public override string Name => "config";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(5);
    public override async Task ExecuteAsync(IServiceProvider services)
    {
        await Task.CompletedTask;
        System.Diagnostics.Debug.WriteLine("[Pipeline] Config loaded");
    }
}

public class ThemeStep : BaseStep
{
    public override string Name => "theme";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(5);
    public override async Task ExecuteAsync(IServiceProvider services)
    {
        await Task.CompletedTask;
        System.Diagnostics.Debug.WriteLine("[Pipeline] Theme loaded");
    }
}

public class DIContainerStep : BaseStep
{
    public override string Name => "di";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(5);
    public override async Task ExecuteAsync(IServiceProvider services)
    {
        await Task.CompletedTask;
        System.Diagnostics.Debug.WriteLine("[Pipeline] DI container ready");
    }
}

public class GrpcConnectStep : BaseStep
{
    public override string Name => "grpc";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(10);

    public override async Task ExecuteAsync(IServiceProvider services)
    {
        var grpc = services.GetRequiredService<GrpcClient>();
        var health = await grpc.CheckHealthCoreAsync();
        if (health is null)
            System.Diagnostics.Debug.WriteLine("[Pipeline] gRPC: backend offline (degraded)");
        else
            System.Diagnostics.Debug.WriteLine("[Pipeline] gRPC connected");
    }
}

public class EventBusInitStep : BaseStep
{
    public override string Name => "eventbus";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(5);
    public override bool Critical => true;

    public override async Task ExecuteAsync(IServiceProvider services)
    {
        var bus = services.GetRequiredService<IEventBus>();
        await bus.PublishAsync("kernel.starting");
        System.Diagnostics.Debug.WriteLine("[Pipeline] EventBus ready");
    }
}

public class PluginLoadStep : BaseStep
{
    public override string Name => "plugins";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(10);
    public override bool Critical => false;

    public override async Task ExecuteAsync(IServiceProvider services)
    {
        var pluginService = services.GetRequiredService<PluginService>();
        var count = pluginService.LoadAll();
        System.Diagnostics.Debug.WriteLine($"[Pipeline] Plugins loaded: {count}");
        await Task.CompletedTask;
    }
}

public class HudInitStep : BaseStep
{
    public override string Name => "hud";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(5);

    public override async Task ExecuteAsync(IServiceProvider services)
    {
        System.Diagnostics.Debug.WriteLine("[Pipeline] HUD initialized");
        await Task.CompletedTask;
    }
}

public class ReadyStep : BaseStep
{
    public override string Name => "ready";
    public override TimeSpan Timeout => TimeSpan.FromSeconds(5);

    public override async Task ExecuteAsync(IServiceProvider services)
    {
        var bus = services.GetRequiredService<IEventBus>();
        await bus.PublishAsync("kernel.ready");
        System.Diagnostics.Debug.WriteLine("[Pipeline] Application ready");
    }
}
