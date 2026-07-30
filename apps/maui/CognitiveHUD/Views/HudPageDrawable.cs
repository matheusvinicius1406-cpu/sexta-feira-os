namespace SextaFeira.CognitiveHUD.Pages;

/// <summary>
/// MAUI IDrawable for HUD page backgrounds.
/// Renders subtle ambient effects (grid, glow ring, particles)
/// using MAUI's native ICanvas — no SkiaSharp dependency needed.
///
/// This is assigned to each page's GraphicsView by HudBasePage.
/// The 60 FPS render loop calls Invalidate() → Draw().
/// </summary>
public class HudPageDrawable : IDrawable
{
    private readonly Random _random = new();
    private float _pulseTime;

    /// <summary>Current depth level changes the ring style.</summary>
    public int Depth { get; set; }

    /// <summary>Primary glow color from theme.</summary>
    public Color PrimaryColor { get; set; } = Color.FromArgb("#00E5FF");

    /// <summary>Secondary accent color from theme.</summary>
    public Color SecondaryColor { get; set; } = Color.FromArgb("#7C4DFF");

    public void Update(float deltaSeconds)
    {
        _pulseTime += deltaSeconds;
    }

    public void Draw(ICanvas canvas, RectF dirtyRect)
    {
        float cx = dirtyRect.Center.X;
        float cy = dirtyRect.Center.Y;

        // ── 1. Background ───────────────────────────────
        canvas.FillColor = Color.FromArgb("#0A0A12");
        canvas.FillRectangle(dirtyRect);

        // ── 2. Subtle grid ──────────────────────────────
        canvas.StrokeColor = PrimaryColor.WithAlpha(0.03f);
        canvas.StrokeSize = 0.5f;
        float spacing = 40f;
        for (float x = dirtyRect.Left; x <= dirtyRect.Right; x += spacing)
            canvas.DrawLine(x, dirtyRect.Top, x, dirtyRect.Bottom);
        for (float y = dirtyRect.Top; y <= dirtyRect.Bottom; y += spacing)
            canvas.DrawLine(dirtyRect.Left, y, dirtyRect.Right, y);

        // ── 3. Crosshair ───────────────────────────────
        canvas.StrokeColor = PrimaryColor.WithAlpha(0.06f);
        canvas.StrokeSize = 0.5f;
        canvas.DrawLine(cx - 20, cy, cx + 20, cy);
        canvas.DrawLine(cx, cy - 20, cx, cy + 20);

        // ── 4. Pulse ring ──────────────────────────────
        float pulseRadius = 60f + 20f * MathF.Sin(_pulseTime * 1.5f);
        float alpha = 0.08f + 0.04f * MathF.Sin(_pulseTime * 1.5f + 1f);
        canvas.StrokeColor = PrimaryColor.WithAlpha(alpha);
        canvas.StrokeSize = 1f;
        canvas.DrawCircle(cx, cy, pulseRadius);

        // ── 5. Depth indicator rings ──────────────────
        for (int i = 1; i <= Depth; i++)
        {
            float ringR = 80f + i * 120f;
            float ringAlpha = 0.03f * i;
            canvas.StrokeColor = PrimaryColor.WithAlpha(ringAlpha);
            canvas.StrokeSize = 0.5f + 0.3f * i;
            canvas.StrokeDashPattern = i % 2 == 0 ? new float[] { 4, 8 } : null;
            canvas.DrawCircle(cx, cy, ringR);
            canvas.StrokeDashPattern = null;

            // Cardinal dots
            for (int d = 0; d < 4; d++)
            {
                float angle = d * 90f * MathF.PI / 180f;
                float dx = cx + ringR * MathF.Cos(angle - MathF.PI / 2f);
                float dy = cy + ringR * MathF.Sin(angle - MathF.PI / 2f);
                canvas.FillColor = PrimaryColor.WithAlpha(ringAlpha * 2f);
                canvas.FillCircle(dx, dy, 1.5f * i);
            }
        }
    }
}
