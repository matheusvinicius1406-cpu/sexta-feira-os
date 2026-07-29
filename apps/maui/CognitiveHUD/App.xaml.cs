namespace SextaFeira.CognitiveHUD;

public partial class App : Application
{
    public App()
    {
        InitializeComponent();
    }

    protected override Window CreateWindow(IActivationState? activationState)
    {
        var mainPage = Handler?.MauiContext?.Services.GetRequiredService<MainPage>();
        return new Window(mainPage ?? new MainPage());
    }
}
