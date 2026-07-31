using SextaFeira.CognitiveHUD.Views;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.Pages;

/// <summary>
/// Base class for all 15 HUD pages in the Sexta-Feira Cognitive OS.
///
/// Each page defines its own XAML layout with a single
/// <c>&lt;GraphicsView x:Name="HudCanvas" /&gt;</c> plus module-specific
/// content. This base class provides:
/// - 60 FPS render loop via the page's HudCanvas
/// - HudPageDrawable for ambient HUD effects (grid, glow, pulse rings)
/// - IEventBus for publishing page lifecycle events
/// - Back gesture (bottom-left tap)
/// - Shell route registration
/// </summary>
public abstract class HudBasePage : ContentPage
{
    private IEventBus? _eventBus;
    private IDispatcherTimer? _renderTimer;
    private GraphicsView? _hudCanvas;
    private HudPageDrawable? _drawable;
    private DateTime _lastFrame = DateTime.UtcNow;

    /// <summary>The module identifier for this page (e.g. "memory", "voice").</summary>
    protected abstract string ModuleId { get; }

    /// <summary>The display title shown in the breadcrumb.</summary>
    protected abstract string ModuleTitle { get; }

    /// <summary>The event bus for publishing page lifecycle events.</summary>
    protected IEventBus Bus => _eventBus ??= ResolveService<IEventBus>();

    protected HudBasePage()
    {
        BackgroundColor = Color.FromArgb("#0A0A12");
        Shell.SetNavBarIsVisible(this, false);
    }

    private T ResolveService<T>() where T : class
    {
        var services = App.ServiceProvider ?? Handler?.MauiContext?.Services;
        return services?.GetRequiredService<T>()
            ?? throw new InvalidOperationException($"{typeof(T).Name} not registered in DI");
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();

        // Find the GraphicsView from XAML (named "HudCanvas")
        _hudCanvas = this.FindByName<GraphicsView>("HudCanvas");
        if (_hudCanvas != null)
        {
            // Create the drawable with ambient HUD effects
            _drawable = new HudPageDrawable
            {
                Depth = ResolveDepth(),
                PrimaryColor = Color.FromArgb("#00E5FF"),
                SecondaryColor = Color.FromArgb("#7C4DFF"),
            };
            _hudCanvas.Drawable = _drawable;
            _hudCanvas.StartInteraction += OnCanvasTap;
            _hudCanvas.BackgroundColor = Colors.Transparent;

            StartRenderLoop();
        }

        _ = Bus.PublishAsync($"hud.{ModuleId}.opened", new Dictionary<string, object> { ["module"] = ModuleId });
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        _renderTimer?.Stop();
        _renderTimer = null;
        if (_hudCanvas != null)
        {
            _hudCanvas.StartInteraction -= OnCanvasTap;
            _hudCanvas.Drawable = null;
        }
        _ = Bus.PublishAsync($"hud.{ModuleId}.closed", new Dictionary<string, object> { ["module"] = ModuleId });
    }

    /// <summary>
    /// Returns the navigation depth for this page. Override to customize.
    /// Default: 1 (Level 1 module).
    /// </summary>
    protected virtual int ResolveDepth() => 1;

    private void StartRenderLoop()
    {
        _renderTimer = Dispatcher.CreateTimer();
        _renderTimer.Interval = TimeSpan.FromMilliseconds(16); // ~60 FPS
        _renderTimer.Tick += OnRenderTick;
        _renderTimer.Start();
        _lastFrame = DateTime.UtcNow;
    }

    private void OnRenderTick(object? sender, EventArgs e)
    {
        var now = DateTime.UtcNow;
        float dt = (float)(now - _lastFrame).TotalSeconds;
        if (dt > 0.1f) dt = 0.016f;

        _drawable?.Update(dt);
        _hudCanvas?.Invalidate();
        _lastFrame = now;
    }

    /// <summary>
    /// Handles tap on the HUD canvas. Bottom-left quadrant = back navigation.
    /// </summary>
    protected virtual void OnCanvasTap(object? sender, TouchEventArgs e)
    {
        if (e.Touches.Length == 0 || _hudCanvas == null) return;
        var point = e.Touches[0];
        float width = (float)_hudCanvas.Width;
        float height = (float)_hudCanvas.Height;
        if (point.X < width * 0.25 && point.Y > height * 0.75)
            if (Shell.Current is not null)
                _ = Shell.Current.GoToAsync("..");
    }
}
