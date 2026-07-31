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
        // Use static fallback if Handler is not ready yet.
        var services = ServiceProvider ?? Handler?.MauiContext?.Services
            ?? throw new InvalidOperationException(
                "No service provider available at window creation — MauiProgram must set App.ServiceProvider.");

        _ = RunStartupPipelineAsync(services);

        // No `new MainPage()` fallback: the page needs its view model injected,
        // and a hand-constructed one could never satisfy that.
        return new Window(services.GetRequiredService<MainPage>());
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
