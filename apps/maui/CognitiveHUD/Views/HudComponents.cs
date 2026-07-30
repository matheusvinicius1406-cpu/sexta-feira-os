using SkiaSharp;
using SextaFeira.UIEngine.Themes;

namespace SextaFeira.CognitiveHUD.Views;

// ═══════════════════════════════════════════════════════════
//  HUD CORE COMPONENTS — FASE 7
//  All components are reusable, SkiaSharp-based, and designed
//  for the radial HUD navigation system.
// ═══════════════════════════════════════════════════════════

// ── HudTheme ─────────────────────────────────────────────

/// <summary>HUD-specific theme extension with glow, blur, and hologram colors.</summary>
public record HudTheme(
    SKColor PrimaryGlow,
    SKColor SecondaryGlow,
    SKColor HologramColor,
    SKColor Background,
    SKColor TextPrimary,
    SKColor TextSecondary,
    float GlowRadius = 20f,
    float HologramOpacity = 0.3f,
    bool HologramEnabled = true);

// ── HudAnimation ─────────────────────────────────────────

/// <summary>Animation easing types for HUD transitions.</summary>
public enum HudEasing
{
    Linear, EaseIn, EaseOut, EaseInOut, Elastic, Bounce, Spring
}

/// <summary>Base animation controller for HUD elements.</summary>
public class HudAnimation
{
    public float Duration { get; set; } = 0.3f;
    public HudEasing Easing { get; set; } = HudEasing.EaseOut;
    public bool IsPlaying { get; private set; }
    public float Progress { get; private set; }

    private DateTime _startTime;

    public void Play()
    {
        IsPlaying = true;
        _startTime = DateTime.UtcNow;
        Progress = 0f;
    }

    public void Update(float deltaSeconds)
    {
        if (!IsPlaying) return;
        var elapsed = (float)(DateTime.UtcNow - _startTime).TotalSeconds;
        Progress = Math.Clamp(elapsed / Duration, 0f, 1f);
        if (Progress >= 1f) IsPlaying = false;
    }

    public float ApplyEasing(float t) => Easing switch
    {
        HudEasing.Linear => t,
        HudEasing.EaseOut => 1f - (1f - t) * (1f - t),
        HudEasing.EaseInOut => t < 0.5f ? 2f * t * t : 1f - (float)Math.Pow(-2f * t + 2f, 2f) / 2f,
        HudEasing.Elastic => (float)(Math.Pow(2, -10 * t) * Math.Sin((t - 0.075) * (2 * Math.PI) / 0.3) + 1),
        _ => t,
    };

    public float Value => ApplyEasing(Progress);
}

// ── HudPhysics ───────────────────────────────────────────

/// <summary>Simple physics simulation for particle effects.</summary>
public class HudPhysics
{
    public struct Particle
    {
        public float X, Y, Vx, Vy, Life, MaxLife;
        public SKColor Color;
        public float Radius;
        public bool IsAlive => Life > 0;
    }

    private readonly List<Particle> _particles = new();
    private readonly Random _random = new();

    public IReadOnlyList<Particle> Particles => _particles.AsReadOnly();
    public int ParticleCount => _particles.Count;

    public void Emit(float x, float y, int count, SKColor color, float speed = 100f)
    {
        for (int i = 0; i < count; i++)
        {
            var angle = (float)(_random.NextDouble() * Math.PI * 2);
            var spd = (float)(_random.NextDouble() * speed);
            _particles.Add(new Particle
            {
                X = x, Y = y,
                Vx = (float)Math.Cos(angle) * spd,
                Vy = (float)Math.Sin(angle) * spd,
                Life = 1f,
                MaxLife = 1f,
                Color = color.WithAlpha((byte)(color.Alpha * 0.7f)),
                Radius = (float)(_random.NextDouble() * 3 + 1),
            });
        }
    }

    public void Update(float dt)
    {
        for (int i = _particles.Count - 1; i >= 0; i--)
        {
            var p = _particles[i];
            p.X += p.Vx * dt;
            p.Y += p.Vy * dt;
            p.Life -= dt * 0.5f;
            if (p.Life <= 0) _particles.RemoveAt(i);
            else _particles[i] = p;
        }
    }

    public void Draw(SKCanvas canvas)
    {
        foreach (var p in _particles)
        {
            var alpha = (byte)(p.Color.Alpha * p.Life);
            canvas.DrawCircle(p.X, p.Y, p.Radius, new SKPaint
            {
                Color = p.Color.WithAlpha(alpha),
                IsAntialias = true,
            });
        }
    }

    public void Clear() => _particles.Clear();
}

// ── HudParticles ─────────────────────────────────────────

/// <summary>Ambient particle system for background effects.</summary>
public class HudParticles
{
    private HudPhysics _physics = new();
    private readonly Random _random = new();
    private SKColor _color;

    public HudParticles(SKColor color) => _color = color;

    public void Update(float dt, float centerX, float centerY, float radius)
    {
        _physics.Update(dt);
        if (_physics.ParticleCount < 20)
            _physics.Emit(centerX + (float)(_random.NextDouble() - 0.5) * radius * 2,
                          centerY + (float)(_random.NextDouble() - 0.5) * radius * 2,
                          1, _color, 20f);
    }

    public void Draw(SKCanvas canvas) => _physics.Draw(canvas);
}

// ── HudGlow ──────────────────────────────────────────────

/// <summary>Glow effect renderer using radial gradients.</summary>
public class HudGlow
{
    public SKColor Color { get; set; } = SKColors.Cyan;
    public float Radius { get; set; } = 30f;
    public float Intensity { get; set; } = 0.5f;
    public bool IsVisible { get; set; } = true;

    private float _pulseTime;

    public void Update(float dt) => _pulseTime += dt;

    public void Draw(SKCanvas canvas, float x, float y)
    {
        if (!IsVisible || Intensity <= 0) return;

        using var paint = new SKPaint
        {
            Shader = SKShader.CreateRadialGradient(
                new SKPoint(x, y), Radius,
                new[] { Color.WithAlpha((byte)(Intensity * 80)),
                        Color.WithAlpha((byte)(Intensity * 30)),
                        Color.WithAlpha(0) },
                new[] { 0f, 0.5f, 1f },
                SKShaderTileMode.Clamp),
            IsAntialias = true,
        };
        canvas.DrawCircle(x, y, Radius, paint);
    }
}

// ── HudBlur ──────────────────────────────────────────────

/// <summary>Blur effect overlay (approximation via transparent layers).</summary>
public class HudBlur
{
    public float BlurRadius { get; set; } = 10f;
    public SKColor TintColor { get; set; } = SKColors.Black.WithAlpha(128);

    public void Draw(SKCanvas canvas, SKRect bounds)
    {
        using var paint = new SKPaint
        {
            Color = TintColor,
            MaskFilter = SKMaskFilter.CreateBlur(SKBlurStyle.Normal, BlurRadius),
        };
        canvas.DrawRect(bounds, paint);
    }
}

// ── HudEffects ───────────────────────────────────────────

/// <summary>Composite effect system for HUD elements.</summary>
public class HudEffects
{
    public HudGlow Glow { get; } = new();
    public HudBlur Blur { get; } = new();
    public bool HologramEnabled { get; set; }

    public void Update(float dt)
    {
        Glow.Update(dt);
    }

    public void ApplyGlow(SKCanvas canvas, float x, float y)
    {
        Glow.Draw(canvas, x, y);
    }
}

// ── HudTransitions ───────────────────────────────────────

/// <summary>Manages transitions between HUD states.</summary>
public class HudTransitions
{
    private HudAnimation _animation = new();
    public event Action? OnTransitionComplete;

    public bool IsTransitioning => _animation.IsPlaying;
    public float Progress => _animation.Value;

    public void StartTransition(float duration = 0.3f)
    {
        _animation = new HudAnimation { Duration = duration, Easing = HudEasing.EaseOut };
        _animation.Play();
    }

    public void Update(float dt)
    {
        _animation.Update(dt);
        if (!_animation.IsPlaying && _animation.Progress >= 1f)
            OnTransitionComplete?.Invoke();
    }
}

// ── HudGestures ──────────────────────────────────────────

/// <summary>Gesture state for HUD interaction.</summary>
public enum HudGestureType
{
    None, Tap, LongPress, SwipeUp, SwipeDown, SwipeLeft, SwipeRight, Pinch, Rotate
}

/// <summary>Tracks gesture state for HUD elements.</summary>
public class HudGestures
{
    public HudGestureType CurrentGesture { get; private set; } = HudGestureType.None;
    public float GestureProgress { get; private set; }
    public SKPoint GestureStart { get; private set; }
    public SKPoint GestureCurrent { get; private set; }

    public event Action<HudGestureType>? OnGestureDetected;

    public void OnTap(SKPoint position)
    {
        CurrentGesture = HudGestureType.Tap;
        GestureStart = position;
        OnGestureDetected?.Invoke(HudGestureType.Tap);
    }

    public void OnDrag(SKPoint start, SKPoint current)
    {
        GestureStart = start;
        GestureCurrent = current;
        var dx = current.X - start.X;
        var dy = current.Y - start.Y;
        if (Math.Abs(dx) > Math.Abs(dy))
            CurrentGesture = dx > 0 ? HudGestureType.SwipeRight : HudGestureType.SwipeLeft;
        else
            CurrentGesture = dy > 0 ? HudGestureType.SwipeDown : HudGestureType.SwipeUp;
        GestureProgress = Math.Max(Math.Abs(dx), Math.Abs(dy)) / 200f;
    }

    public void Reset() => CurrentGesture = HudGestureType.None;
}

// ── HudNodes ─────────────────────────────────────────────

/// <summary>A node in the HUD radial menu.</summary>
public class HudNode
{
    public string Id { get; set; } = "";
    public string Label { get; set; } = "";
    public string Icon { get; set; } = "";
    public SKColor Color { get; set; }
    public float Angle { get; set; }
    public float Distance { get; set; } = 100f;
    public float Scale { get; set; } = 1f;
    public float Opacity { get; set; } = 1f;
    public bool IsActive { get; set; }
    public bool IsExpanded { get; set; }
    public List<HudNode> Children { get; set; } = new();
    public HudEffects Effects { get; } = new();
}

// ── HudMenu ──────────────────────────────────────────────

/// <summary>Radial/semi-circle menu renderer.</summary>
public class HudMenu
{
    public List<HudNode> Nodes { get; } = new();
    public float StartAngle { get; set; } = -90f;
    public float ArcAngle { get; set; } = 180f;
    public float Radius { get; set; } = 120f;
    public float ItemRadius { get; set; } = 25f;
    public bool IsVisible { get; set; } = true;

    private HudAnimation _openAnim = new() { Duration = 0.4f, Easing = HudEasing.EaseOut };

    public void Open()
    {
        _openAnim.Play();
        IsVisible = true;
    }

    public void Close()
    {
        IsVisible = false;
    }

    public void Update(float dt)
    {
        _openAnim.Update(dt);
        var progress = _openAnim.Value;
        foreach (var node in Nodes)
        {
            node.Opacity = progress;
            node.Scale = progress;
        }
    }

    public void Draw(SKCanvas canvas, float centerX, float centerY, HudTheme theme)
    {
        if (!IsVisible) return;

        var step = Nodes.Count > 1 ? ArcAngle / (Nodes.Count - 1) : 0;

        for (int i = 0; i < Nodes.Count; i++)
        {
            var node = Nodes[i];
            var angle = (StartAngle + i * step) * MathF.PI / 180f;
            var x = centerX + MathF.Cos(angle) * Radius * node.Scale;
            var y = centerY + MathF.Sin(angle) * Radius * node.Scale;

            // Connection line
            using var linePaint = new SKPaint
            {
                Color = theme.PrimaryGlow.WithAlpha((byte)(40 * node.Opacity)),
                StrokeWidth = 1,
                IsAntialias = true,
                Style = SKPaintStyle.Stroke,
            };
            canvas.DrawLine(centerX, centerY, x, y, linePaint);

            // Node circle
            var r = ItemRadius * node.Scale;
            using var fillPaint = new SKPaint
            {
                Color = node.Color.WithAlpha((byte)(200 * node.Opacity)),
                IsAntialias = true,
            };
            canvas.DrawCircle(x, y, r, fillPaint);

            // Glow
            if (node.IsActive)
            {
                node.Effects.ApplyGlow(canvas, x, y);
            }

            // Label
            using var textPaint = new SKPaint
            {
                Color = theme.TextPrimary.WithAlpha((byte)(200 * node.Opacity)),
                TextSize = 10,
                IsAntialias = true,
                TextAlign = SKTextAlign.Center,
            };
            canvas.DrawText(node.Label, x, y + r + 12, textPaint);
        }
    }
}

// ── HudNavigation ────────────────────────────────────────

/// <summary>HUD navigation state machine.</summary>
public enum HudNavigationState
{
    Idle, Expanding, Selecting, Transitioning, Collapsing
}

/// <summary>Manages HUD navigation state and depth.</summary>
public class HudNavigation
{
    public HudNavigationState State { get; private set; } = HudNavigationState.Idle;
    public int CurrentDepth { get; private set; }
    public HudNode? SelectedNode { get; private set; }
    public Stack<HudNode> History { get; } = new();
    public event Action<HudNavigationState>? OnStateChanged;

    public void Expand()
    {
        State = HudNavigationState.Expanding;
        OnStateChanged?.Invoke(State);
    }

    public void Select(HudNode node)
    {
        SelectedNode = node;
        if (node.Children.Count > 0)
        {
            History.Push(node);
            CurrentDepth++;
            State = HudNavigationState.Transitioning;
        }
        OnStateChanged?.Invoke(State);
    }

    public void GoBack()
    {
        if (History.Count > 0)
        {
            History.Pop();
            CurrentDepth--;
            State = CurrentDepth == 0 ? HudNavigationState.Idle : HudNavigationState.Selecting;
        }
        OnStateChanged?.Invoke(State);
    }

    public void Collapse()
    {
        History.Clear();
        CurrentDepth = 0;
        State = HudNavigationState.Collapsing;
        OnStateChanged?.Invoke(State);
    }

    public void Reset()
    {
        State = HudNavigationState.Idle;
        OnStateChanged?.Invoke(State);
    }
}

// ── HudPanel ─────────────────────────────────────────────

/// <summary>A content panel within the HUD.</summary>
public class HudPanel
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public bool IsVisible { get; set; }
    public SKRect Bounds { get; set; }
    public HudAnimation OpenAnim { get; } = new() { Duration = 0.3f, Easing = HudEasing.EaseOut };

    public void Open()
    {
        IsVisible = true;
        OpenAnim.Play();
    }

    public void Close()
    {
        IsVisible = false;
    }

    public void Update(float dt) => OpenAnim.Update(dt);
}

// ── HudStateMachine ──────────────────────────────────────

/// <summary>Finite state machine for HUD behavior.</summary>
public class HudStateMachine
{
    private string _currentState = "closed";
    private readonly Dictionary<string, Func<Task>> _transitions = new();

    public string CurrentState => _currentState;

    public void DefineTransition(string fromState, string toState, Func<Task> handler)
    {
        _transitions[$"{fromState}->{toState}"] = handler;
    }

    public async Task TransitionTo(string newState)
    {
        var key = $"{_currentState}->{newState}";
        if (_transitions.TryGetValue(key, out var handler))
        {
            await handler();
            _currentState = newState;
        }
    }
}

// ── HudOverlay ───────────────────────────────────────────

/// <summary>Overlay/glass panel background.</summary>
public class HudOverlay
{
    public SKColor Color { get; set; } = SKColors.Black.WithAlpha(100);
    public bool IsVisible { get; set; }

    public void Draw(SKCanvas canvas, SKRect bounds)
    {
        if (!IsVisible) return;
        using var paint = new SKPaint
        {
            Color = Color,
            MaskFilter = SKMaskFilter.CreateBlur(SKBlurStyle.Normal, 20f),
        };
        canvas.DrawRoundRect(bounds, 16, 16, paint);
    }
}

// ── HudCamera ────────────────────────────────────────────

/// <summary>Virtual camera for HUD viewport.</summary>
public class HudCamera
{
    public float Zoom { get; set; } = 1f;
    public SKPoint Pan { get; set; }
    public float Rotation { get; set; }

    public void Apply(SKCanvas canvas)
    {
        canvas.Scale(Zoom, Zoom);
        canvas.Translate(Pan.X, Pan.Y);
        canvas.RotateDegrees(Rotation);
    }
}

// ── HudViewport ──────────────────────────────────────────

/// <summary>Viewport/clipping region for HUD rendering.</summary>
public class HudViewport
{
    public SKRect Bounds { get; set; }
    public HudCamera Camera { get; } = new();
    public SKColor ClearColor { get; set; } = SKColors.Black;

    public void BeginDraw(SKCanvas canvas)
    {
        canvas.Clear(ClearColor);
        canvas.Save();
        canvas.ClipRect(Bounds);
        Camera.Apply(canvas);
    }

    public void EndDraw(SKCanvas canvas)
    {
        canvas.Restore();
    }
}

// ── HudScene ─────────────────────────────────────────────

/// <summary>Top-level HUD scene that orchestrates all components.</summary>
public class HudScene
{
    public HudViewport Viewport { get; } = new();
    public HudMenu Menu { get; } = new();
    public HudNavigation Navigation { get; } = new();
    public HudParticles? Particles { get; set; }
    public HudOverlay Overlay { get; } = new();
    public HudEffects Effects { get; } = new();
    public HudTransitions Transitions { get; } = new();
    public HudGestures Gestures { get; } = new();
    public HudStateMachine StateMachine { get; } = new();
    public List<HudPanel> Panels { get; } = new();
    public HudTheme Theme { get; set; }

    public HudScene(HudTheme theme)
    {
        Theme = theme;
        Particles = new HudParticles(theme.PrimaryGlow);
    }

    public void Update(float dt)
    {
        Transitions.Update(dt);
        Menu.Update(dt);
        Particles?.Update(dt, Viewport.Bounds.MidX, Viewport.Bounds.MidY, 100f);
        Effects.Update(dt);
    }

    public void Draw(SKCanvas canvas)
    {
        Viewport.BeginDraw(canvas);

        Particles?.Draw(canvas);
        Menu.Draw(canvas, Viewport.Bounds.MidX, Viewport.Bounds.MidY, Theme);
        Overlay.Draw(canvas, Viewport.Bounds);

        foreach (var panel in Panels.Where(p => p.IsVisible))
        {
            Effects.ApplyGlow(canvas, panel.Bounds.MidX, panel.Bounds.MidY);
        }

        Viewport.EndDraw(canvas);
    }
}

// ── HudSound ─────────────────────────────────────────────

/// <summary>HUD sound effects controller.</summary>
public class HudSound
{
    public bool Enabled { get; set; } = true;
    public float Volume { get; set; } = 0.5f;

    public void PlayOpen() { /* platform-specific audio */ }
    public void PlayClose() { /* platform-specific audio */ }
    public void PlaySelect() { /* platform-specific audio */ }
    public void PlayTransition() { /* platform-specific audio */ }
}

// ── HudAccessibility ─────────────────────────────────────

/// <summary>HUD accessibility settings.</summary>
public class HudAccessibility
{
    public bool ReducedMotion { get; set; }
    public bool HighContrast { get; set; }
    public float TextScale { get; set; } = 1f;
    public bool ScreenReaderEnabled { get; set; }
}

// ── HudLayout ────────────────────────────────────────────

/// <summary>HUD layout calculator — positions elements based on viewport.</summary>
public static class HudLayout
{
    public static float CenterX(SKRect bounds) => bounds.MidX;
    public static float CenterY(SKRect bounds) => bounds.MidY;

    public static SKRect RingBounds(SKRect viewport, float ringRadius)
    {
        var cx = viewport.MidX;
        var cy = viewport.MidY;
        return new SKRect(cx - ringRadius, cy - ringRadius, cx + ringRadius, cy + ringRadius);
    }

    public static float CalculateRingRadius(SKRect viewport, int nodeCount)
    {
        var maxRadius = Math.Min(viewport.Width, viewport.Height) * 0.35f;
        var minRadius = nodeCount * 25f;
        return Math.Min(maxRadius, Math.Max(minRadius, 120f));
    }
}
