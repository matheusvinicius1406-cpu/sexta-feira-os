using SextaFeira.CognitiveHUD.ViewModels;
using SextaFeira.CognitiveHUD.Views;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.CognitiveHUD;

/// <summary>
/// The main HUD page — the only "screen" in the Sexta-Feira Cognitive OS.
/// 
/// Supports multi-layer navigation:
/// - Tap core → expand radial menu (Level 1: modules)
/// - Tap module → transition animation → Level 2 (sub-modules)
/// - Tap sub-module → transition → Level 3 (actions)
/// - Back button → reverse transition → previous level
/// - Root button → instant return to Level 1
/// </summary>
public partial class MainPage : ContentPage
{
    private readonly CoreHudViewModel _viewModel;
    private HudCanvasDrawable? _drawable;
    private IDispatcherTimer? _renderTimer;
    private DateTime _lastFrameTime = DateTime.UtcNow;

    public MainPage()
    {
        InitializeComponent();

        _viewModel = Handler?.MauiContext?.Services.GetRequiredService<CoreHudViewModel>()
            ?? throw new InvalidOperationException("ViewModel not registered");

        BindingContext = _viewModel;

        // Bind HUD canvas interactions
        HudCanvas.StartInteraction += OnCanvasStartInteraction;
        HudCanvas.EndInteraction += OnCanvasEndInteraction;
        HudCanvas.CancelInteraction += (s, e) => { }; // no-op required by MAUI

        // Subscribe to navigation depth changes to update UI
        _viewModel.PropertyChanged += OnViewModelPropertyChanged;

        // Start the 60 FPS render loop
        StartRenderLoop();
    }

    // ── Render Loop (60 FPS) ───────────────────────────────
    private void StartRenderLoop()
    {
        _drawable = new HudCanvasDrawable(_viewModel);
        HudCanvas.Drawable = _drawable;
        _lastFrameTime = DateTime.UtcNow;

        _renderTimer = Dispatcher.CreateTimer();
        _renderTimer.Interval = TimeSpan.FromMilliseconds(16);
        _renderTimer.Tick += OnRenderTick;
        _renderTimer.Start();
    }

    private void OnRenderTick(object? sender, EventArgs e)
    {
        var now = DateTime.UtcNow;
        float deltaSeconds = (float)(now - _lastFrameTime).TotalSeconds;

        if (deltaSeconds > 0.1f) deltaSeconds = 0.016f;

        _viewModel.Update(deltaSeconds);
        HudCanvas.Invalidate();
        _lastFrameTime = now;
    }

    // ── ViewModel property sync ────────────────────────────
    private void OnViewModelPropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        switch (e.PropertyName)
        {
            case nameof(CoreHudViewModel.CanGoBack):
                BackButton.IsVisible = _viewModel.CanGoBack;
                break;

            case nameof(CoreHudViewModel.CurrentDepth):
                UpdateDepthIndicators(_viewModel.CurrentDepth);
                RootButton.IsVisible = _viewModel.CurrentDepth >= 2;
                break;

            case nameof(CoreHudViewModel.BreadcrumbText):
                BreadcrumbLabel.Text = _viewModel.BreadcrumbText;
                break;

            case nameof(CoreHudViewModel.IsConnected):
                StatusDot.Color = _viewModel.IsConnected
                    ? Color.FromArgb("#00E676")
                    : Color.FromArgb("#666666");
                break;

            case nameof(CoreHudViewModel.ConnectionStatus):
                StatusLabel.Text = _viewModel.ConnectionStatus;
                break;

            case nameof(CoreHudViewModel.StatusDotColor):
                StatusDot.Color = Color.FromArgb(_viewModel.StatusDotColor);
                break;
        }
    }

    private void UpdateDepthIndicators(int depth)
    {
        // Level 1 dot
        Level1Dot.Color = depth >= 0
            ? Color.FromArgb("#00E5FF")
            : Color.FromArgb("#333355");

        // Level 2 dot (Memória sub-levels)
        Level2Dot.Color = depth >= 1
            ? Color.FromArgb("#7C4DFF")
            : Color.FromArgb("#333355");

        // Level 3 dot (Conhecimento sub-levels)
        Level3Dot.Color = depth >= 2
            ? Color.FromArgb("#FFD600")
            : Color.FromArgb("#333355");

        // Depth dot color
        DepthDot.TextColor = depth switch
        {
            0 => Color.FromArgb("#00E5FF"),
            1 => Color.FromArgb("#7C4DFF"),
            _ => Color.FromArgb("#FFD600"),
        };
    }

    // ── Canvas Interaction ─────────────────────────────────
    private void OnCanvasStartInteraction(object? sender, TouchEventArgs e)
    {
        if (e.Touches.Length == 0) return;

        var tapPoint = e.Touches[0];
        float centerX = (float)HudCanvas.Width / 2f;
        float centerY = (float)HudCanvas.Height / 2f;

        // 1. Check core circle tap
        float dx = tapPoint.X - centerX;
        float dy = tapPoint.Y - centerY;
        float coreRadius = _viewModel.CoreCircle.Radius * 1.3f;
        bool hitCore = dx * dx + dy * dy <= coreRadius * coreRadius;

        if (hitCore)
        {
            // If expanded and in a sub-level, tap center = go back
            if (_viewModel.IsCoreExpanded && _viewModel.CanGoBack)
            {
                _viewModel.GoBack();
            }
            else
            {
                _viewModel.ToggleCoreExpand();
            }
            return;
        }

        // 2. Check radial menu items
        if (_viewModel.RadialMenu != null && _viewModel.IsMenuVisible)
        {
            var item = _viewModel.RadialMenu.GetItemAt(tapPoint);
            if (item != null)
            {
                item.State = HudNodeState.Active;
                _ = _viewModel.SelectModule(item.ModuleId);
            }
        }
        else if (!_viewModel.IsCoreExpanded)
        {
            // 3. Tap anywhere to expand
            _viewModel.Expand();
        }
    }

    private static void OnCanvasEndInteraction(object? sender, TouchEventArgs e) { }

    // ── Button handlers ────────────────────────────────────
    private void OnExpandClicked(object? sender, EventArgs e)
    {
        _viewModel.ToggleCoreExpand();
    }

    private void OnBackClicked(object? sender, EventArgs e)
    {
        _viewModel.GoBack();
    }

    private void OnRootClicked(object? sender, EventArgs e)
    {
        _viewModel.GoToRoot();
    }
}
