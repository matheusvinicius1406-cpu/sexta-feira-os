using Microsoft.Maui.Graphics;
using SextaFeira.CognitiveHUD.ViewModels;
using SextaFeira.UIEngine.Themes;

namespace SextaFeira.CognitiveHUD.Views;

/// <summary>
/// Custom IDrawable that renders the entire HUD scene each frame.
/// 
/// Render order:
/// 1. Background + subtle grid
/// 2. Ambient orbital particles
/// 3. Depth indicator rings (concentric circles showing current level)
/// 4. Core circle (the "brain")
/// 5. Radial menu items (when expanded)
/// 6. Transition particle burst effects
/// </summary>
public class HudCanvasDrawable : IDrawable
{
    private const float DepthRingSpacing = 120f;

    private readonly CoreHudViewModel _viewModel;

    public HudCanvasDrawable(CoreHudViewModel viewModel)
    {
        _viewModel = viewModel ?? throw new ArgumentNullException(nameof(viewModel));
    }

    public void Draw(ICanvas canvas, RectF dirtyRect)
    {
        ITheme theme = _viewModel.CurrentTheme;
        float centerX = dirtyRect.Center.X;
        float centerY = dirtyRect.Center.Y;
        int depth = _viewModel.CurrentDepth;

        // ── 1. Background ───────────────────────────────
        canvas.FillColor = theme.Background;
        canvas.FillRectangle(dirtyRect);

        // ── 2. Subtle grid ──────────────────────────────
        DrawSubtleGrid(canvas, dirtyRect, theme);

        // ── 3. Depth indicator rings ────────────────────
        if (depth > 0)
        {
            DrawDepthRings(canvas, centerX, centerY, depth, theme);
        }

        // ── 4. Ambient orbital particles ───────────────
        foreach (var orbital in _viewModel.AmbientOrbitals)
        {
            orbital.CenterX = centerX;
            orbital.CenterY = centerY;
            orbital.Draw(canvas);
        }

        // ── 5. Core Circle ─────────────────────────────
        if (_viewModel.CoreCircle.IsVisible)
        {
            _viewModel.CoreCircle.Draw(canvas, dirtyRect);
        }

        // ── 6. Radial Menu ─────────────────────────────
        var radialMenu = _viewModel.RadialMenu;
        if (radialMenu != null && _viewModel.IsMenuVisible)
        {
            radialMenu.CenterX = centerX;
            radialMenu.CenterY = centerY;
            radialMenu.Draw(canvas, dirtyRect);
        }

        // ── 7. Transition particle burst ───────────────
        _viewModel.TransitionBurst.Draw(canvas);

        // ── 8. Breadcrumb overlay on canvas ────────────
        if (depth > 0)
        {
            DrawBreadcrumbOverlay(canvas, centerX, dirtyRect, theme);
        }
    }

    private static void DrawDepthRings(ICanvas canvas, float cx, float cy, int depth, ITheme theme)
    {
        for (int i = 1; i <= depth; i++)
        {
            float ringRadius = CoreHudViewModel.CoreRadiusDefault + DepthRingSpacing * i;
            float alpha = 0.04f + 0.03f * i;
            float thickness = 0.5f + 0.3f * i;

            // Filled ring (very subtle)
            canvas.FillColor = theme.Primary.WithAlpha(alpha * 0.3f);
            canvas.FillCircle(cx, cy, ringRadius);

            // Ring stroke
            canvas.StrokeColor = theme.Primary.WithAlpha(alpha);
            canvas.StrokeSize = thickness;
            canvas.StrokeDashPattern = i % 2 == 0
                ? new float[] { 4, 8 }
                : null;
            canvas.DrawCircle(cx, cy, ringRadius);
            canvas.StrokeDashPattern = null;

            // Small indicator dots at cardinal points
            float dotRadius = 1.5f * i;
            for (int d = 0; d < 4; d++)
            {
                float angle = d * 90f * MathF.PI / 180f;
                float dx = cx + ringRadius * MathF.Cos(angle - MathF.PI / 2f);
                float dy = cy + ringRadius * MathF.Sin(angle - MathF.PI / 2f);

                canvas.FillColor = theme.Primary.WithAlpha(alpha * 1.5f);
                canvas.FillCircle(dx, dy, dotRadius);
            }
        }
    }

    private static void DrawBreadcrumbOverlay(ICanvas canvas, float cx, RectF bounds, ITheme theme)
    {
        float y = bounds.Top + 14f;
        float fadeWidth = 60f;

        // Background pill for readability
        canvas.FillColor = theme.Background.WithAlpha(0.6f);
        canvas.FillRoundedRectangle(cx - fadeWidth - 10f, y - 4f, fadeWidth * 2f + 20f, 16f, 8f);
    }

    private static void DrawSubtleGrid(ICanvas canvas, RectF bounds, ITheme theme)
    {
        canvas.StrokeColor = theme.TextSecondary.WithAlpha(0.03f);
        canvas.StrokeSize = 0.5f;

        float spacing = 40f;

        for (float x = bounds.Left; x <= bounds.Right; x += spacing)
            canvas.DrawLine(x, bounds.Top, x, bounds.Bottom);

        for (float y = bounds.Top; y <= bounds.Bottom; y += spacing)
            canvas.DrawLine(bounds.Left, y, bounds.Right, y);

        // Crosshair
        canvas.StrokeColor = theme.Primary.WithAlpha(0.08f);
        canvas.StrokeSize = 0.5f;
        canvas.DrawLine(bounds.Center.X - 20f, bounds.Center.Y, bounds.Center.X + 20f, bounds.Center.Y);
        canvas.DrawLine(bounds.Center.X, bounds.Center.Y - 20f, bounds.Center.X, bounds.Center.Y + 20f);
    }
}
