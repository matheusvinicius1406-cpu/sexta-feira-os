using Microsoft.Maui.Graphics;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Controls;

/// <summary>
/// An item that continuously orbits around the core circle.
/// Used for non-interactive status indicators (e.g., live monitoring,
/// connection status, activity indicators).
/// 
/// Unlike RadialMenuItem, OrbitalItem is not clickable — it provides
/// ambient visual information through motion and color.
/// </summary>
public class OrbitalItem
{
    // ── Orbit ──────────────────────────────────────────────
    public float CenterX { get; set; }
    public float CenterY { get; set; }
    public float OrbitRadius { get; set; } = 100f;
    public float OrbitSpeed { get; set; } = 0.3f; // cycles per second
    public float StartAngle { get; set; }
    public bool Clockwise { get; set; } = true;

    // ── Visual ─────────────────────────────────────────────
    public float Radius { get; set; } = 4f;
    public Color Color { get; set; } = NeonColors.Primary;
    public float Opacity { get; set; } = 0.6f;
    public bool PulseOpacity { get; set; } = true;
    public string? Label { get; set; }
    public string? Icon { get; set; }

    // ── Runtime ────────────────────────────────────────────
    private float _currentAngle;

    public float X { get; private set; }
    public float Y { get; private set; }

    public OrbitalItem(float startAngle = 0f)
    {
        StartAngle = startAngle;
        _currentAngle = startAngle;
    }

    /// <summary>
    /// Updates orbital position. Call each frame.
    /// </summary>
    public void Update(float deltaSeconds)
    {
        float direction = Clockwise ? 1f : -1f;
        _currentAngle += deltaSeconds * OrbitSpeed * 360f * direction;

        if (_currentAngle > 360f) _currentAngle -= 360f;
        if (_currentAngle < 0f) _currentAngle += 360f;

        float rad = _currentAngle * MathF.PI / 180f;
        X = CenterX + OrbitRadius * MathF.Sin(rad);
        Y = CenterY - OrbitRadius * MathF.Cos(rad);
    }

    /// <summary>
    /// Draws this orbital item on the canvas.
    /// </summary>
    public void Draw(ICanvas canvas)
    {
        float opacity = Opacity;

        if (PulseOpacity)
        {
            float pulse = 0.7f + 0.3f * MathF.Sin(_currentAngle * MathF.PI / 180f * 2f);
            opacity *= pulse;
        }

        // ── Dot ────────────────────────────────────────────
        canvas.FillColor = Color.WithAlpha(opacity);
        canvas.FillCircle(X, Y, Radius);

        // ── Glow ────────────────────────────────────────────
        canvas.FillColor = Color.WithAlpha(opacity * 0.15f);
        canvas.FillCircle(X, Y, Radius * 3f);

        // ── Label ───────────────────────────────────────────
        if (!string.IsNullOrEmpty(Label))
        {
            canvas.FontColor = NeonColors.TextSecondary.WithAlpha(opacity);
            canvas.FontSize = 8f;
            canvas.Font = Microsoft.Maui.Graphics.Font.Default;
            canvas.DrawString(Label, X, Y + Radius + 10f, HorizontalAlignment.Center);
        }

        // ── Icon ────────────────────────────────────────────
        if (!string.IsNullOrEmpty(Icon))
        {
            canvas.FontColor = Color.WithAlpha(opacity);
            canvas.FontSize = 12f;
            canvas.DrawString(Icon, X, Y, HorizontalAlignment.Center);
        }
    }

    /// <summary>
    /// Resets the orbital position to its start angle.
    /// </summary>
    public void Reset()
    {
        _currentAngle = StartAngle;
    }
}
