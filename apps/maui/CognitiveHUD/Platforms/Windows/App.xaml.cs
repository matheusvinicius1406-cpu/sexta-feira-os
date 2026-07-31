using Microsoft.UI.Xaml;

namespace SextaFeira.CognitiveHUD.Platforms.Windows;

public partial class App : MauiWinUIApplication
{
    public App()
    {
        // WinUI wraps startup failures as stowed exceptions (0xC000027B).
        // They never reach AppDomain.UnhandledException, so the only way to
        // see what actually went wrong is to hook the XAML application here,
        // before InitializeComponent runs.
        UnhandledException += (_, e) =>
        {
            MauiProgram.LogStartupCrash("WinUI", e.Exception);
            e.Handled = false;
        };

        this.InitializeComponent();
    }

    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}
