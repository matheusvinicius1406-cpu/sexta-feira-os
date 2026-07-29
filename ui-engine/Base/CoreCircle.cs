using Microsoft.Maui.Graphics;

namespace SextaFeira.UIEngine.Base;

/// <summary>
/// The central circle — the "brain" of Sexta-Feira OS.
/// 
/// Features:
/// - Continuous soft pulse animation
/// - Glow effect that responds to state changes
/// - Ripple on click/tap
/// - Displays status text in the center
/// - Acts as the anchor for all radial navigation
/// </summary>
public class CoreCircle : HudNode
{
    private const float BaseRadius = 60f;

    // ── Pulse Animation ─────────────────────────────────────
    private float _pulsePhase;
    public float PulsePhase
    {
        get => _pulsePhase;
        set
        {
            _pulsePhase = value;
            OnPropertyChanged();
        }
    }

    private float _pulseScale = 1f;
    public float PulseScale
    {
        get => _pulseScale;
        set
        {
            _pulseScale = Math.Clamp(value, 0.5f, 2f);
            OnPropertyChanged();
        }
    }

    public float PulseSpeed { get; set; } = 1.5f; // cycles per second

    // ── Display ─────────────────────────────────────────────
    private string _statusText = "Sexta-Feira";
    public string StatusText
    {
        get => _statusText;
        set
        {
            _statusText = value;
            OnPropertyChanged();
        }
    }

    private string _subtitleText = "toque para ativar";
    public string SubtitleText
    {
        get => _subtitleText;
        set
        {
            _subtitleText = value;
            OnPropertyChanged();
        }
    }

    // ── Tap ripple ──────────────────────────────────────────
    private float _rippleProgress;
    public float RippleProgress
    {
        get => _rippleProgress;
        set
        {
            _rippleProgress = Math.Clamp(value, 0f, 1f);
            OnPropertyChanged();
        }
    }

    public CoreCircle() : base("core", "Sexta-Feira", BaseRadius)
    {
        Color = NeonColors.Primary;
        GlowColor = NeonColors.Glow;
        GlowIntensity = 0.6f;
    }

    // ── Pulse update (call each frame) ──────────────────────
    public void UpdatePulse(float deltaSeconds)
    {
        _pulsePhase += deltaSeconds * PulseSpeed * MathF.PI * 2f;
        if (_pulsePhase > MathF.PI * 2f)
            _pulsePhase -= MathF.PI * 2f;

        float rawPulse = MathF.Sin(_pulsePhase);
        PulseScale = 1f + (rawPulse * 0.08f);

        float glowPhase = MathF.Sin(_pulsePhase + MathF.PI * 0.5f);
        GlowIntensity = 0.5f + (glowPhase * 0.3f);
    }

    // ── Trigger ripple effect ───────────────────────────────
    public void TriggerRipple()
    {
        RippleProgress = 0.01f;
    }

    public void UpdateRipple(float deltaSeconds)
    {
        if (_rippleProgress <= 0f || _rippleProgress >= 1f)
            return;

        _rippleProgress += deltaSeconds * 2.5f;
        if (_rippleProgress >= 1f)
            _rippleProgress = 1f;
    }

    // ── Draw ────────────────────────────────────────────────
    public override void Draw(ICanvas canvas, RectF bounds)
    {
        if (!IsVisible) return;

        float centerX = bounds.Center.X;
        float centerY = bounds.Center.Y;

        // ── Outer glow (layered semitransparent circles) ────
        if (GlowIntensity > 0f)
        {
            float glowRadius = Radius * 2.5f * _pulseScale;
            float glowAlpha = GlowIntensity * 0.25f;

            canvas.FillColor = GlowColor.WithAlpha(glowAlpha);
            canvas.FillCircle(centerX, centerY, glowRadius);

            // Second glow layer
            canvas.FillColor = GlowColor.WithAlpha(glowAlpha * 0.5f);
            canvas.FillCircle(centerX, centerY, glowRadius * 1.5f);

            // Third glow layer
            canvas.FillColor = GlowColor.WithAlpha(glowAlpha * 0.2f);
            canvas.FillCircle(centerX, centerY, glowRadius * 2.2f);
        }

        // ── Outer ring ──────────────────────────────────────
        float currentRadius = Radius * _pulseScale;
        canvas.StrokeColor = Color.WithAlpha(0.6f);
        canvas.StrokeSize = 2f;
        canvas.DrawCircle(centerX, centerY, currentRadius * 1.1f);

        // ── Main circle ─────────────────────────────────────
        canvas.FillColor = Color.WithAlpha(0.15f);
        canvas.FillCircle(centerX, centerY, currentRadius);

        // ── Inner area ──────────────────────────────────────
        canvas.FillColor = Color.WithAlpha(0.3f);
        canvas.FillCircle(centerX, centerY, currentRadius * 0.7f);

        // ── Core dot ────────────────────────────────────────
        canvas.FillColor = Color;
        canvas.FillCircle(centerX, centerY, currentRadius * 0.15f);

        // ── Inner ring ──────────────────────────────────────
        canvas.StrokeColor = Color.WithAlpha(0.4f);
        canvas.StrokeSize = 1.5f;
        canvas.DrawCircle(centerX, centerY, currentRadius * 0.4f);

        // ── Status text ─────────────────────────────────────
        canvas.FontColor = NeonColors.TextPrimary;
        canvas.FontSize = 11f;
        canvas.Font = Microsoft.Maui.Graphics.Font.Default;
        canvas.DrawString(
            _statusText,
            centerX, centerY - currentRadius - 20f,
            HorizontalAlignment.Center);

        // ── Subtitle ────────────────────────────────────────
        canvas.FontColor = NeonColors.TextSecondary;
        canvas.FontSize = 9f;
        canvas.DrawString(
            _subtitleText,
            centerX, centerY + currentRadius + 14f,
            HorizontalAlignment.Center);

        // ── Ripple effect ───────────────────────────────────
        if (_rippleProgress > 0f && _rippleProgress < 1f)
        {
            float rippleRadius = currentRadius * (1f + _rippleProgress * 2f);
            float rippleAlpha = 1f - _rippleProgress;

            canvas.StrokeColor = Color.WithAlpha(rippleAlpha * 0.5f);
            canvas.StrokeSize = 2f * (1f - _rippleProgress) + 0.5f;
            canvas.DrawCircle(centerX, centerY, rippleRadius);
        }
    }
}
