using Microsoft.Maui.Graphics;

namespace SextaFeira.UIEngine.Base;

/// <summary>
/// A standalone glow effect that can be rendered behind any HudNode.
/// Uses layered semitransparent circles (MAUI Graphics doesn't support
/// FillColor = gradient).
/// </summary>
public class GlowCircle
{
    // ── Configuration ───────────────────────────────────────
    public Color Color { get; set; } = NeonColors.Glow;
    public float Intensity { get; set; } = 0.5f;
    public float SizeMultiplier { get; set; } = 2.5f;
    public int LayerCount { get; set; } = 4;
    public float PulseSpeed { get; set; } = 1.0f;
    public bool Animated { get; set; } = true;

    // ── Runtime state ───────────────────────────────────────
    private float _phase;

    /// <summary>
    /// Updates the glow animation phase. Call each frame.
    /// </summary>
    public void Update(float deltaSeconds)
    {
        if (!Animated) return;

        _phase += deltaSeconds * PulseSpeed * MathF.PI * 2f;
        if (_phase > MathF.PI * 2f)
            _phase -= MathF.PI * 2f;
    }

    /// <summary>
    /// Draws the glow effect centered at the given position
    /// using layered semitransparent circles.
    /// </summary>
    public void Draw(ICanvas canvas, float centerX, float centerY, float baseRadius)
    {
        if (Intensity <= 0f) return;

        float animatedIntensity = Animated
            ? Intensity * (0.7f + 0.3f * MathF.Sin(_phase))
            : Intensity;

        for (int i = LayerCount - 1; i >= 0; i--)
        {
            float layerRatio = (i + 1f) / LayerCount;
            float layerRadius = baseRadius * SizeMultiplier * layerRatio;
            float layerAlpha = (animatedIntensity / LayerCount) * (1f - i * 0.25f);

            if (layerAlpha <= 0f) continue;

            canvas.FillColor = Color.WithAlpha(layerAlpha);
            canvas.FillCircle(centerX, centerY, layerRadius);
        }
    }

    /// <summary>
    /// Resets the animation phase to zero.
    /// </summary>
    public void Reset()
    {
        _phase = 0f;
    }
}
