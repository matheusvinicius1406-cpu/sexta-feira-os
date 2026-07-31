using System.Diagnostics;
using System.Globalization;
using SkiaSharp;
using SkiaSharp.Views.Maui;
using SextaFeira.UIEngine.Design;
using SextaFeira.UIEngine.Reactor;

namespace SextaFeira.CognitiveHUD;

/// <summary>
/// ARC — the only screen in Sexta-Feira OS.
///
/// The reactor is painted by <see cref="ReactorRenderer"/> at 60 fps and never
/// leaves the geometric centre. Navigation is orbital: tap the core to open
/// the module ring, tap a module to open its children, tap the core again to
/// go back. No sidebar, drawer, tab bar or back arrow.
///
/// Reactor state is never set by a control — it follows what the assistant is
/// doing. See docs/design-system/05-MOVIMENTO.md §1.
/// </summary>
public partial class MainPage : ContentPage
{
    private readonly ReactorRenderer _renderer = new();
    private readonly ReactorModel _model = new();
    private readonly ArcBrain _brain;
    private readonly List<Label> _labels = new();

    private IDispatcherTimer? _renderTimer;
    private IDispatcherTimer? _telemetryTimer;
    private readonly Stopwatch _clock = Stopwatch.StartNew();
    private TimeSpan _lastFrame;
    private readonly DateTime _startedAt = DateTime.Now;

    private SKPoint _pointer = new(-9999, -9999);
    private ArcItem[] _items = ArcModules.ItemsFor(0, -1);
    private float _density = 1f;
    private SKTypeface? _wordmarkFace;

    public MainPage()
    {
        InitializeComponent();
        _brain = new ArcBrain(_model, ApplyChip);
        _wordmarkFace = LoadWordmarkTypeface();
        BuildLabelPool(ArcModules.All.Length);
    }

    /// <summary>
    /// Skia cannot see fonts that are only registered with MAUI, so the
    /// wordmark face is loaded from the file MauiFont copied next to the
    /// executable. A null result is survivable — Skia falls back to the
    /// default face and the chrome gradient still renders.
    /// </summary>
    private static SKTypeface? LoadWordmarkTypeface()
    {
        try
        {
            var path = Path.Combine(AppContext.BaseDirectory, "Rajdhani-Bold.ttf");
            return File.Exists(path) ? SKTypeface.FromFile(path) : null;
        }
        catch { return null; }
    }

    // ── Lifecycle ───────────────────────────────────────────

    protected override void OnAppearing()
    {
        base.OnAppearing();
        _density = (float)DeviceDisplay.MainDisplayInfo.Density;
        if (_density <= 0f) _density = 1f;

        _renderTimer = Dispatcher.CreateTimer();
        _renderTimer.Interval = TimeSpan.FromMilliseconds(16);   // ~60 fps
        _renderTimer.Tick += OnFrame;
        _renderTimer.Start();

        _telemetryTimer = Dispatcher.CreateTimer();
        _telemetryTimer.Interval = TimeSpan.FromSeconds(1);
        _telemetryTimer.Tick += (_, _) => UpdateTelemetry();
        _telemetryTimer.Start();

        UpdateTelemetry();
        _ = RunBootAsync();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        // A reactor spinning behind a hidden page is pure battery drain.
        _renderTimer?.Stop(); _renderTimer = null;
        _telemetryTimer?.Stop(); _telemetryTimer = null;
    }

    private static readonly string[] BootSteps =
    {
        "INITIALIZING", "REACTOR ONLINE", "MOUNTING MEMORY", "LINKING AGENTS",
        "CALIBRATING VOICE", "HANDSHAKE OK", "ARC READY",
    };

    private async Task RunBootAsync()
    {
        for (int i = 0; i < BootSteps.Length; i++)
        {
            BootLog.Text = BootSteps[i];
            BootTrack.Color = ArcColor(ArcTokens.Plasma);
            BootTrack.WidthRequest = 190 * (i + 1) / (double)BootSteps.Length;
            await Task.Delay(260);
        }
        await Task.Delay(420);
        // The reactor is already turning behind the veil — it fades to reveal
        // a running system, never one starting from zero.
        await Boot.FadeTo(0, 900, Easing.CubicOut);
        Boot.IsVisible = false;
    }

    // ── Frame ───────────────────────────────────────────────

    private void OnFrame(object? sender, EventArgs e)
    {
        var now = _clock.Elapsed;
        float dt = (float)(now - _lastFrame).TotalSeconds;
        _lastFrame = now;

        _items = ArcModules.ItemsFor(_model.Depth, _model.ActiveIndex);
        _model.ItemCount = _items.Length;
        _model.HoverIndex = _renderer.HitTest(_pointer, _items.Length, _model);
        _model.Proximity = Proximity();

        _model.Update(dt);
        _brain.Tick(dt);

        Surface.InvalidateSurface();
        PositionLabels();
    }

    private float Proximity()
    {
        float r = _renderer.CoreRadius;
        if (r <= 0f) return 0f;
        var c = _renderer.Center;
        float dx = _pointer.X - c.X, dy = _pointer.Y - c.Y;
        return Math.Clamp(1f - (MathF.Sqrt(dx * dx + dy * dy) - r) / (r * 2.6f), 0f, 1f);
    }

    private void OnPaintSurface(object? sender, SKPaintSurfaceEventArgs e)
    {
        var canvas = e.Surface.Canvas;
        var size = new SKSize(e.Info.Width, e.Info.Height);

        _renderer.Render(canvas, size, _model);
        _renderer.DrawOrbit(canvas, _items, _model);
        _renderer.DrawWordmark(canvas, "J.A.R.V.I.S.", _wordmarkFace, _model);

        // Identity block clears the reactor and the wordmark. Canvas units are
        // pixels; MAUI positions in device-independent units.
        IdentityBlock.TranslationY =
            _renderer.CoreRadius * ArcGeometry.ClockOffset / _density;
        IdentityBlock.Opacity = _model.Depth > 0 ? 0.30 : 1.0;
    }

    private void OnSurfaceTouch(object? sender, SKTouchEventArgs e)
    {
        _pointer = e.Location;

        if (e.ActionType == SKTouchAction.Pressed)
        {
            if (_renderer.HitsCore(_pointer, _model))
            {
                _model.Ripple();
                SetDepth(_model.Depth == 0 ? 1 : _model.Depth == 2 ? 1 : 0);
            }
            else
            {
                int hit = _renderer.HitTest(_pointer, _items.Length, _model);
                if (hit >= 0)
                {
                    _model.Ripple();
                    if (_model.Depth == 1)
                    {
                        _model.ActiveIndex = hit;
                        SetDepth(2);
                        _brain.Observe(BrainSignal.Navigate);
                    }
                    else if (_model.Depth == 2)
                    {
                        _brain.Observe(BrainSignal.Command);
                    }
                }
            }
        }

        e.Handled = true;
    }

    // ── Orbital captions ────────────────────────────────────

    private void BuildLabelPool(int count)
    {
        for (int i = 0; i < count; i++)
        {
            var label = new Label
            {
                FontFamily = "ArcDataMedium",
                FontSize = 8,
                CharacterSpacing = 1.9,
                TextTransform = TextTransform.Uppercase,
                TextColor = ArcColor(ArcTokens.InkLo),
                InputTransparent = true,
                Opacity = 0,
            };
            _labels.Add(label);
            OrbitLabels.Add(label);
        }
    }

    private void PositionLabels()
    {
        for (int i = 0; i < _labels.Count; i++)
        {
            var label = _labels[i];
            if (i >= _items.Length || _model.Open <= 0.01f) { label.Opacity = 0; continue; }

            float eased = ArcMotion.Stagger(_model.Open, i, _items.Length);
            if (eased <= 0.01f) { label.Opacity = 0; continue; }

            var p = _renderer.OrbitPosition(i, _items.Length, _model.Open);
            float hov = _model.HoverIndex == i ? _model.HoverAmount : 0f;
            float iconSize = _renderer.CoreRadius * ArcGeometry.IconSize;

            label.Text = _items[i].Label;
            label.TextColor = hov > 0.5f ? ArcColor(ArcTokens.Ignition) : ArcColor(ArcTokens.InkLo);
            label.Opacity = ArcMotion.Lerp(0.55f, 1f, hov) * eased;

            // SKCanvasView reports pixels; MAUI positions in device-independent
            // units. Forgetting this divide is the classic bug here — on a 3x
            // display every caption lands three times too far from the centre.
            double x = p.X / _density - (label.Width > 0 ? label.Width / 2 : 18);
            double y = (p.Y + iconSize * 1.5f) / _density;
            AbsoluteLayout.SetLayoutBounds(label,
                new Rect(x, y, AbsoluteLayout.AutoSize, AbsoluteLayout.AutoSize));
        }
    }

    private static Color ArcColor(SKColor c) =>
        Color.FromRgba(c.Red, c.Green, c.Blue, c.Alpha);

    // ── Navigation ──────────────────────────────────────────

    private void SetDepth(int depth)
    {
        _model.Depth = depth;
        if (depth == 0) _model.ActiveIndex = -1;
        _model.HoverIndex = -1;

        Pip1.Color = depth >= 1 ? ArcColor(ArcTokens.Plasma) : ArcColor(ArcTokens.InkGhost);
        Pip2.Color = depth >= 2 ? ArcColor(ArcTokens.Plasma) : ArcColor(ArcTokens.InkGhost);
        Crumb.Text = depth switch
        {
            0 => "CORE",
            1 => "CORE · MODULES",
            _ => $"CORE · {ArcModules.All[_model.ActiveIndex].Label.ToUpperInvariant()}",
        };
    }

    // ── Telemetry ───────────────────────────────────────────

    private void UpdateTelemetry()
    {
        var now = DateTime.Now;
        Clock.Text = now.ToString("HH:mm");
        DateOut.Text = now.ToString("ddd dd MMM", CultureInfo.InvariantCulture).ToUpperInvariant();

        var up = now - _startedAt;
        UptimeOut.Text = $"{(int)up.TotalHours:00}:{up.Minutes:00}:{up.Seconds:00}";

        // Load follows the reactor's actual state rather than being decorative.
        double load = _model.State == ReactorState.Thinking
            ? 62 + Random.Shared.NextDouble() * 30
            : 8 + Random.Shared.NextDouble() * 14;
        LoadOut.Text = load.ToString("00.0", CultureInfo.InvariantCulture) + " %";

        bool offline = _model.State is ReactorState.Offline or ReactorState.Error;
        LatencyOut.Text = offline ? "— — —" : $"{6 + Random.Shared.Next(22):000} MS";
        LinkOut.Text = _model.State == ReactorState.Offline
            ? "LINK SEVERED" : "GRPC · 127.0.0.1:50051";

        int h = now.Hour;
        string part = h < 12 ? "MORNING" : h < 18 ? "AFTERNOON" : "EVENING";
        Greeting.Text = $"GOOD {part}, MATHEUS";
    }

    private void ApplyChip(ReactorState state)
    {
        StatusText.Text = ReactorStates.For(state).Caption.ToUpperInvariant();

        var accent = state switch
        {
            ReactorState.Error => ArcTokens.Breach,
            ReactorState.Warning => ArcTokens.Caution,
            ReactorState.Offline or ReactorState.Sleep => ArcTokens.InkLo,
            _ => ArcTokens.Plasma,
        };

        StatusDot.Color = ArcColor(accent);
        StatusText.TextColor = state is ReactorState.Error or ReactorState.Warning
            ? ArcColor(accent)
            : ArcColor(ArcTokens.Ink);
        StatusChip.Stroke = new SolidColorBrush(ArcColor(accent.Fade(0.5f)));
    }
}
