using Microsoft.Maui.Graphics;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Controls;

/// <summary>
/// A single item in the radial menu — represents a module or action.
/// 
/// Each item has:
/// - Orbit position (angle + distance from center)
/// - Icon and label
/// - Glow on hover/active
/// - Size variants (default: 60dp radius, or smaller for denser menus)
/// </summary>
public class RadialMenuItem : HudNode
{
    // ── Orbit configuration ─────────────────────────────────
    public float Angle { get; set; }          // Degrees, 0 = top
    public float OrbitRadius { get; set; }    // Distance from center

    public float AngleRadians => Angle * MathF.PI / 180f;

    // ── Visual ──────────────────────────────────────────────
    public string Icon { get; set; }          // Emoji or icon character
    public Color IconColor { get; set; } = NeonColors.TextPrimary;
    public float IconSize { get; set; } = 20f;
    public bool ShowLabel { get; set; } = true;
    public string ModuleId { get; set; }

    // ── Animation state ─────────────────────────────────────
    public float CurrentAngle { get; set; }
    public float CurrentOrbitRadius { get; set; }

    /// <summary>
    /// Callback invoked when this item is selected (clicked/tapped).
    /// </summary>
    public Func<Task>? OnSelected { get; set; }

    public RadialMenuItem(
        string moduleId,
        string label,
        string icon,
        Color color,
        float angle,
        float orbitRadius)
        : base($"module:{moduleId}", label, 30f)
    {
        ModuleId = moduleId;
        Icon = icon;
        Color = color;
        Angle = angle;
        OrbitRadius = orbitRadius;
        CurrentAngle = angle;
        CurrentOrbitRadius = orbitRadius;
    }

    // ── Orbital position update ─────────────────────────────
    public void UpdateOrbitPosition(float centerX, float centerY)
    {
        float rad = CurrentAngle * MathF.PI / 180f;
        X = centerX + CurrentOrbitRadius * MathF.Sin(rad);
        Y = centerY - CurrentOrbitRadius * MathF.Cos(rad);
    }

    // ── Hit test override ──────────────────────────────────
    public override bool HitTest(PointF point)
    {
        if (!IsVisible || !IsInteractive) return false;

        float dx = point.X - X;
        float dy = point.Y - Y;
        return dx * dx + dy * dy <= (Radius * 1.2f) * (Radius * 1.2f);
    }

    // ── Draw ────────────────────────────────────────────────
    public override void Draw(ICanvas canvas, RectF bounds)
    {
        if (!IsVisible) return;

        // ── Glow (when active/hovered) ──────────────────────
        bool isActive = State == HudNodeState.Active || State == HudNodeState.Hovered;
        if (isActive && GlowIntensity > 0f)
        {
            float glowRadius = Radius * 2f;
            canvas.FillColor = GlowColor.WithAlpha(GlowIntensity * 0.2f);
            canvas.FillCircle(X, Y, glowRadius);
        }

        // ── Background circle ───────────────────────────────
        Color bgColor = isActive
            ? Color.WithAlpha(0.3f)
            : Color.WithAlpha(0.1f);
        canvas.FillColor = bgColor;
        canvas.FillCircle(X, Y, Radius);

        // ── Border ──────────────────────────────────────────
        canvas.StrokeColor = isActive ? Color : Color.WithAlpha(0.4f);
        canvas.StrokeSize = isActive ? 2.5f : 1.5f;
        canvas.DrawCircle(X, Y, Radius);

        // ── Inner ring (active only) ────────────────────────
        if (isActive)
        {
            canvas.StrokeColor = Color.WithAlpha(0.3f);
            canvas.StrokeSize = 1f;
            canvas.DrawCircle(X, Y, Radius * 0.7f);
        }

        // ── Icon ────────────────────────────────────────────
        canvas.FontColor = isActive ? Color : IconColor.WithAlpha(0.7f);
        canvas.FontSize = IconSize;
        canvas.Font = Microsoft.Maui.Graphics.Font.Default;
        canvas.DrawString(Icon, X, Y, HorizontalAlignment.Center);

        // ── Label ───────────────────────────────────────────
        if (ShowLabel)
        {
            float labelY = Y + Radius + 14f;
            canvas.FontColor = isActive
                ? NeonColors.TextPrimary
                : NeonColors.TextSecondary;
            canvas.FontSize = 9f;
            canvas.DrawString(Label, X, labelY, HorizontalAlignment.Center);
        }
    }
}
