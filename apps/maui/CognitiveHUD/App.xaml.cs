using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD;

public partial class App : Application
{
    /// <summary>Static service provider set by MauiProgram after builder.Build().</summary>
    public static IServiceProvider? ServiceProvider { get; set; }

    public App()
    {
        InitializeComponent();
        // Register Shell routes for all 15 HUD pages
        MauiProgram.RegisterShellRoutes();
    }

    protected override Window CreateWindow(IActivationState? activationState)
    {
        // Use static fallback if Handler is not ready yet
        var services = ServiceProvider ?? Handler?.MauiContext?.Services;
        if (services is not null)
        {
            _ = RunStartupPipelineAsync(services);
        }

        var mainPage = services?.GetRequiredService<MainPage>() ?? new MainPage();
        return new Window(mainPage);
    }

    private static async Task RunStartupPipelineAsync(IServiceProvider services)
    {
        try
        {
            var pipeline = services.GetRequiredService<MauiStartupPipeline>();
            var success = await pipeline.RunAsync(services);
            System.Diagnostics.Debug.WriteLine(
                success ? "[App] Startup pipeline completed successfully"
                        : $"[App] Startup pipeline completed with errors: {string.Join(", ", pipeline.Errors)}");
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[App] Startup pipeline failed: {ex.Message}");
        }
    }
}
