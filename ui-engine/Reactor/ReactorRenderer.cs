using System.Text;
using SkiaSharp;
using SextaFeira.UIEngine.Design;

namespace SextaFeira.UIEngine.Reactor;

/// <summary>
/// Paints the ARC reactor onto an <see cref="SKCanvas"/>.
///
/// Performance contract (docs/design-system/07-CHECKLISTS.md §2):
///   • paints are fields, never allocated per frame
///   • one clip and one shader per plate ring, not one per plate
///   • no text — labels are MAUI controls positioned from
///     <see cref="OrbitPosition"/>, because 8px text drawn into a canvas
///     is unreadable next to the native font rasteriser
/// </summary>
public sealed class ReactorRenderer : IDisposable
{
    // ── Reusable paints ─────────────────────────────────────
    private readonly SKPaint _fill   = new() { IsAntialias = true, Style = SKPaintStyle.Fill };
    private readonly SKPaint _stroke = new() { IsAntialias = true, Style = SKPaintStyle.Stroke };
    private readonly SKPaint _add    = new() { IsAntialias = true, Style = SKPaintStyle.Fill,
                                               BlendMode = SKBlendMode.Plus };
    private readonly SKPaint _addStroke = new() { IsAntialias = true, Style = SKPaintStyle.Stroke,
                                                  BlendMode = SKBlendMode.Plus };

    private readonly SKPathEffect _dash = SKPathEffect.CreateDash(new[] { 1f, 7f }, 0f);

    // The wordmark is the one place text belongs on this canvas: at
    // 0.42 R it is large enough that Skia's rasteriser is fine, and it
    // needs a gradient fill that no MAUI Label can produce.
    private readonly SKPaint _text = new() { IsAntialias = true, Style = SKPaintStyle.Fill };
    private readonly SKPaint _textGlow = new()
    {
        IsAntialias = true, Style = SKPaintStyle.Fill, BlendMode = SKBlendMode.Plus,
        MaskFilter = SKMaskFilter.CreateBlur(SKBlurStyle.Normal, 9f),
    };

    // ── Brushed-metal sweep ─────────────────────────────────
    // Two specular highlights — one strong at 0.115, one weak at 0.675 —
    // rotating together. That sweep is what sells the chrome; a static
    // gradient reads as flat plastic no matter how well tuned.
    private static readonly SKColor MetalSpec2 =
        ArcTokens.Lerp(ArcTokens.MetalLight, ArcTokens.MetalSpec, 0.55f);

    private static readonly SKColor[] MetalRamp =
    {
        ArcTokens.MetalMid,    ArcTokens.MetalLight, ArcTokens.MetalSpec,
        ArcTokens.MetalLight,  ArcTokens.MetalShadow, ArcTokens.MetalDeep,
        ArcTokens.MetalShadow, ArcTokens.MetalMid,   ArcTokens.MetalLight,
        MetalSpec2,            ArcTokens.MetalMid,   ArcTokens.MetalShadow,
        ArcTokens.MetalMid,    ArcTokens.MetalMid,
    };

    private static readonly float[] MetalStops =
    {
        0.00f, 0.06f, 0.115f, 0.17f, 0.27f, 0.36f, 0.46f,
        0.55f, 0.63f, 0.675f, 0.74f, 0.84f, 0.93f, 1.00f,
    };

    // ── Frame geometry ──────────────────────────────────────
    private float _cx, _cy, _r;

    /// <summary>
    /// Pixels per density-independent unit for the surface being painted.
    /// The host sets this; the core radius clamp depends on it, so leaving it
    /// at 1 on a high-density screen renders the whole HUD a third of size.
    /// </summary>
    public float Density { get; set; } = 1f;

    /// <summary>Core radius in pixels for the last rendered frame.</summary>
    public float CoreRadius => _r;
    public SKPoint Center => new(_cx, _cy);

    /// <summary>Canvas position of orbital item <paramref name="index"/>.
    /// The label layer consumes this; remember to divide by display density
    /// before assigning to a MAUI TranslationX/Y.</summary>
    public SKPoint OrbitPosition(int index, int count, float open)
    {
        float eased = ArcMotion.Stagger(open, index, count);
        float a = ArcGeometry.ItemAngle(index, count) * ArcMotion.Deg2Rad;
        float rad = _r * ArcGeometry.Orbit * eased;
        return new SKPoint(_cx + MathF.Cos(a) * rad, _cy + MathF.Sin(a) * rad);
    }

    // ════════════════════════════════════════════════════════
    public void Render(SKCanvas canvas, SKSize size, ReactorModel m)
    {
        _cx = size.Width / 2f;
        _cy = size.Height / 2f;
        _r  = ArcGeometry.CoreRadius(size.Width, size.Height, Density);

        canvas.Clear(ArcTokens.Void);

        float cs = m.CoreScale;

        DrawNebula(canvas, size, m);
        if (m.Open > 0.01f) DrawOrbitField(canvas, m);
        if (m.HoverAmount > 0.01f && m.Open > 0.1f) DrawWedge(canvas, m);
        if (m.Open > 0.01f) DrawBoundary(canvas, m);

        DrawHudRings(canvas, m, cs);

        // Reactor assembly, outside in.
        DrawMetalBand(canvas, R(ArcGeometry.BezelIn, cs), R(ArcGeometry.BezelOut, cs),
                      m.RotSpecular + m.RotBezel);

        DrawPlateRing(canvas, R(ArcGeometry.PlateAIn, cs), R(ArcGeometry.PlateAOut, cs),
                      ArcGeometry.PlateACount, ArcGeometry.PlateAGap, m.RotPlateA,
                      m.RotSpecular, m.Tint, m.Glow);

        DrawStruts(canvas, m, cs);

        DrawPlateRing(canvas, R(ArcGeometry.PlateBIn, cs), R(ArcGeometry.PlateBOut, cs),
                      ArcGeometry.PlateBCount, ArcGeometry.PlateBGap, m.RotPlateB,
                      m.RotSpecular, m.Tint, m.Glow * 1.1f);

        DrawPlateRing(canvas, R(ArcGeometry.PlateCIn, cs), R(ArcGeometry.PlateCOut, cs),
                      ArcGeometry.PlateCCount, ArcGeometry.PlateCGap, m.RotPlateC,
                      m.RotSpecular, m.Tint, m.Glow * 1.2f);

        DrawLens(canvas, R(ArcGeometry.LensOuter, cs), m);
        DrawHotCore(canvas, R(ArcGeometry.HotCore, cs) * (1f + m.Proximity * 0.10f), m);

        DrawStatusArc(canvas, m, cs);
        DrawSurgeAndRipples(canvas, m);
    }

    private float R(float multiple, float coreScale) => _r * multiple * coreScale;

    // ── Atmosphere ──────────────────────────────────────────
    private void DrawNebula(SKCanvas canvas, SKSize size, ReactorModel m)
    {
        float breath = 0.5f + MathF.Sin(m.Time * 0.55f) * 0.5f;
        float outer = _r * 6.4f;

        using var shader = SKShader.CreateRadialGradient(
            new SKPoint(_cx, _cy), outer,
            new[]
            {
                m.Tint.Fade(0.10f * m.Glow * (0.85f + breath * 0.3f)),
                ArcTokens.Arc.Fade(0.055f * m.Glow),
                ArcTokens.Arc.Fade(0.016f * m.Glow),
                SKColors.Transparent,
            },
            new[] { 0f, 0.24f, 0.58f, 1f },
            SKShaderTileMode.Clamp);

        _fill.Shader = shader;
        canvas.DrawRect(new SKRect(0, 0, size.Width, size.Height), _fill);
        _fill.Shader = null;
    }

    private void DrawOrbitField(SKCanvas canvas, ReactorModel m)
    {
        float rIn = _r * ArcGeometry.WedgeIn, rOut = _r * ArcGeometry.Boundary;
        using var shader = SKShader.CreateRadialGradient(
            new SKPoint(_cx, _cy), rOut,
            new[] { ArcTokens.Arc.Fade(0.030f * m.Open), ArcTokens.Arc.Fade(0.004f * m.Open) },
            new[] { rIn / rOut, 1f },
            SKShaderTileMode.Clamp);

        _fill.Shader = shader;
        canvas.DrawCircle(_cx, _cy, rOut, _fill);
        _fill.Shader = null;
    }

    // ── The signature: an annular sector ────────────────────
    private void DrawWedge(SKCanvas canvas, ReactorModel m)
    {
        float rIn = _r * ArcGeometry.WedgeIn, rOut = _r * ArcGeometry.WedgeOut;
        float spanDeg = 360f / Math.Max(1, m.ItemCount) * ArcGeometry.SectorSpanFactor;
        float startDeg = m.WedgeAngleRad / ArcMotion.Deg2Rad - spanDeg / 2f;

        using var path = Sector(rIn, rOut, startDeg, spanDeg);
        float a = m.HoverAmount * m.Open;

        using var shader = SKShader.CreateRadialGradient(
            new SKPoint(_cx, _cy), rOut,
            new[]
            {
                ArcTokens.Arc.Fade(0.17f * a * 0.35f),
                ArcTokens.Arc.Fade(0.17f * a),
                ArcTokens.Arc.Fade(0.17f * a * 0.72f),
            },
            new[] { rIn / rOut, ArcMotion.Lerp(rIn / rOut, 1f, 0.55f), 1f },
            SKShaderTileMode.Clamp);

        _fill.Shader = shader;
        canvas.DrawPath(path, _fill);
        _fill.Shader = null;

        _stroke.Color = ArcTokens.Arc.Fade(0.46f * a);
        _stroke.StrokeWidth = 1f;
        canvas.DrawPath(path, _stroke);
    }

    private SKPath Sector(float rIn, float rOut, float startDeg, float sweepDeg)
    {
        var outer = new SKRect(_cx - rOut, _cy - rOut, _cx + rOut, _cy + rOut);
        var inner = new SKRect(_cx - rIn,  _cy - rIn,  _cx + rIn,  _cy + rIn);
        var p = new SKPath();
        p.AddArc(outer, startDeg, sweepDeg);
        p.ArcTo(inner, startDeg + sweepDeg, -sweepDeg, false);
        p.Close();
        return p;
    }

    private void DrawBoundary(SKCanvas canvas, ReactorModel m)
    {
        _stroke.Color = ArcTokens.Arc.Fade(0.13f * m.Open);
        _stroke.StrokeWidth = 1f;
        _stroke.PathEffect = _dash;
        canvas.DrawCircle(_cx, _cy, _r * ArcGeometry.Boundary, _stroke);
        _stroke.PathEffect = null;

        DrawSegmentRing(canvas, _r * ArcGeometry.Boundary * 0.985f, 1f,
                        m.Tint.Fade(0.20f * m.Open), 3, 96f, m.RotBound);
    }

    // ── HUD instrumentation ─────────────────────────────────
    private void DrawHudRings(SKCanvas canvas, ReactorModel m, float cs)
    {
        // Ticks
        float rTick = R(ArcGeometry.HudTicks, cs);
        float len = _r * 0.05f;
        _stroke.Color = ArcTokens.Steel.Fade(0.5f * (0.35f + m.Glow * 0.65f));
        _stroke.StrokeWidth = 1f;
        for (int i = 0; i < ArcGeometry.TickCount; i++)
        {
            float a = (m.RotTicks + 360f / ArcGeometry.TickCount * i) * ArcMotion.Deg2Rad;
            float l = i % ArcGeometry.TickEvery == 0 ? len * 2.1f : len;
            float ca = MathF.Cos(a), sa = MathF.Sin(a);
            canvas.DrawLine(_cx + ca * rTick, _cy + sa * rTick,
                            _cx + ca * (rTick + l), _cy + sa * (rTick + l), _stroke);
        }

        DrawSegmentRing(canvas, R(ArcGeometry.HudSegRing, cs), 1.2f,
                        m.Tint.Fade(0.22f * m.Glow), 5, 26f, m.RotHud);
    }

    private void DrawSegmentRing(SKCanvas canvas, float radius, float width,
                                 SKColor color, int count, float gapDeg, float rotDeg)
    {
        float step = 360f / count, span = step - gapDeg;
        var oval = new SKRect(_cx - radius, _cy - radius, _cx + radius, _cy + radius);
        _stroke.Color = color;
        _stroke.StrokeWidth = width;
        for (int i = 0; i < count; i++)
            canvas.DrawArc(oval, rotDeg + i * step, span, false, _stroke);
    }

    // ── Metal ───────────────────────────────────────────────
    private SKShader MetalShader(float rotDeg) =>
        SKShader.CreateSweepGradient(
            new SKPoint(_cx, _cy), MetalRamp, MetalStops,
            SKMatrix.CreateRotationDegrees(rotDeg, _cx, _cy));

    private void DrawMetalBand(SKCanvas canvas, float rIn, float rOut, float rotDeg)
    {
        using var clip = Annulus(rIn, rOut);
        canvas.Save();
        canvas.ClipPath(clip, SKClipOperation.Intersect, true);
        using (var shader = MetalShader(rotDeg))
        {
            _fill.Shader = shader;
            canvas.DrawCircle(_cx, _cy, rOut, _fill);
            _fill.Shader = null;
        }
        canvas.Restore();

        _stroke.StrokeWidth = 1f;
        _stroke.Color = ArcTokens.MetalSpec.Fade(0.20f);
        canvas.DrawCircle(_cx, _cy, rOut - 0.5f, _stroke);
        _stroke.Color = ArcTokens.MetalDeep.Fade(0.85f);
        canvas.DrawCircle(_cx, _cy, rIn + 0.5f, _stroke);
    }

    private SKPath Annulus(float rIn, float rOut)
    {
        var p = new SKPath { FillType = SKPathFillType.EvenOdd };
        p.AddCircle(_cx, _cy, rOut);
        p.AddCircle(_cx, _cy, rIn);
        return p;
    }

    /// <summary>
    /// A ring of bevelled plates with light escaping between them — the
    /// core motif of the reference. All plates share one path so the ring
    /// costs a single clip and a single shader, not one per plate.
    /// </summary>
    private void DrawPlateRing(SKCanvas canvas, float rIn, float rOut, int count,
                               float gapDeg, float rotDeg, float specDeg,
                               SKColor tint, float glow)
    {
        float step = 360f / count, span = step - gapDeg;

        // Escaping light, painted first so the plates sit on top of it.
        using (var clip = Annulus(rIn - 1f, rOut + 1f))
        {
            canvas.Save();
            canvas.ClipPath(clip, SKClipOperation.Intersect, true);
            using var shader = SKShader.CreateRadialGradient(
                new SKPoint(_cx, _cy), rOut * 1.1f,
                new[] { tint.Fade(0.55f * glow), tint.Fade(0.12f * glow) },
                new[] { rIn * 0.6f / (rOut * 1.1f), 1f },
                SKShaderTileMode.Clamp);
            _add.Shader = shader;
            canvas.DrawCircle(_cx, _cy, rOut + 2f, _add);
            _add.Shader = null;
            canvas.Restore();
        }

        using var plates = new SKPath();
        var outerRect = new SKRect(_cx - rOut, _cy - rOut, _cx + rOut, _cy + rOut);
        var innerRect = new SKRect(_cx - rIn,  _cy - rIn,  _cx + rIn,  _cy + rIn);
        for (int i = 0; i < count; i++)
        {
            float a0 = rotDeg + i * step;
            plates.AddArc(outerRect, a0, span);
            plates.ArcTo(innerRect, a0 + span, -span, false);
            plates.Close();
        }

        canvas.Save();
        canvas.ClipPath(plates, SKClipOperation.Intersect, true);
        using (var shader = MetalShader(specDeg))
        {
            _fill.Shader = shader;
            canvas.DrawCircle(_cx, _cy, rOut, _fill);
            _fill.Shader = null;
        }
        canvas.Restore();

        // Bevel — bright outer arc, dark inner arc. Cheap strokes, no clip.
        _stroke.StrokeWidth = 1.4f;
        var bevelOut = new SKRect(_cx - rOut + 0.7f, _cy - rOut + 0.7f,
                                  _cx + rOut - 0.7f, _cy + rOut - 0.7f);
        var bevelIn  = new SKRect(_cx - rIn - 0.7f, _cy - rIn - 0.7f,
                                  _cx + rIn + 0.7f, _cy + rIn + 0.7f);
        for (int i = 0; i < count; i++)
        {
            float a0 = rotDeg + i * step;
            _stroke.Color = ArcTokens.MetalSpec.Fade(0.28f);
            canvas.DrawArc(bevelOut, a0, span, false, _stroke);
            _stroke.Color = ArcTokens.MetalDeep.Fade(0.90f);
            canvas.DrawArc(bevelIn, a0, span, false, _stroke);
        }

        // Cold rim keeps plates readable against the escaping light.
        _stroke.StrokeWidth = 0.8f;
        _stroke.Color = ArcTokens.Lerp(ArcTokens.MetalLight, tint, 0.35f).Fade(0.30f);
        canvas.DrawPath(plates, _stroke);
    }

    /// <summary>Radial coils, each carrying an outward-travelling pulse.</summary>
    private void DrawStruts(SKCanvas canvas, ReactorModel m, float cs)
    {
        float rIn = R(ArcGeometry.StrutIn, cs), rOut = R(ArcGeometry.StrutOut, cs);
        float scale = _r / 78f;
        float halfIn = 3.2f * scale, halfOut = 6.4f * scale;
        int count = ArcGeometry.StrutCount;

        using var body = new SKPath();
        for (int i = 0; i < count; i++)
        {
            float a = (m.RotStrut + i * (360f / count)) * ArcMotion.Deg2Rad;
            float ca = MathF.Cos(a), sa = MathF.Sin(a), px = -sa, py = ca;
            body.MoveTo(_cx + ca * rIn  + px * halfIn,  _cy + sa * rIn  + py * halfIn);
            body.LineTo(_cx + ca * rOut + px * halfOut, _cy + sa * rOut + py * halfOut);
            body.LineTo(_cx + ca * rOut - px * halfOut, _cy + sa * rOut - py * halfOut);
            body.LineTo(_cx + ca * rIn  - px * halfIn,  _cy + sa * rIn  - py * halfIn);
            body.Close();
        }

        canvas.Save();
        canvas.ClipPath(body, SKClipOperation.Intersect, true);
        using (var shader = MetalShader(m.RotSpecular * 0.6f))
        {
            _fill.Shader = shader;
            canvas.DrawCircle(_cx, _cy, rOut, _fill);
            _fill.Shader = null;
        }
        canvas.Restore();

        _stroke.StrokeWidth = 1f;
        _stroke.Color = ArcTokens.MetalSpec.Fade(0.20f);
        canvas.DrawPath(body, _stroke);

        for (int i = 0; i < count; i++)
        {
            float a = (m.RotStrut + i * (360f / count)) * ArcMotion.Deg2Rad;
            float ca = MathF.Cos(a), sa = MathF.Sin(a);
            float phase = (m.Time * 0.55f * m.Spin + i / (float)count) % 1f;
            float pr = ArcMotion.Lerp(rIn, rOut, phase);
            float fade = MathF.Sin(phase * MathF.PI);
            float ex = _cx + ca * pr, ey = _cy + sa * pr, er = halfOut * 3f;

            using var shader = SKShader.CreateRadialGradient(
                new SKPoint(ex, ey), er,
                new[] { m.Tint.Fade(0.70f * fade * m.Glow), m.Tint.Fade(0f) },
                new[] { 0f, 1f }, SKShaderTileMode.Clamp);
            _add.Shader = shader;
            canvas.DrawCircle(ex, ey, er, _add);
            _add.Shader = null;
        }
    }

    /// <summary>The converging throat leading down to the hot core.</summary>
    private void DrawLens(SKCanvas canvas, float rOut, ReactorModel m)
    {
        for (int i = 0; i < ArcGeometry.LensLayers; i++)
        {
            float t = i / (float)(ArcGeometry.LensLayers - 1);
            float radius = rOut * ArcMotion.Lerp(1f, 0.22f, t);
            float a = ArcMotion.Lerp(0.10f, 0.42f, t) * m.Glow;

            _add.Color = ArcTokens.Lerp(m.Tint, ArcTokens.Ignition, t * 0.7f).Fade(a * 0.34f);
            canvas.DrawCircle(_cx, _cy, radius, _add);

            _addStroke.Color = ArcTokens.Lerp(m.Tint, ArcTokens.Ignition, t).Fade(a);
            _addStroke.StrokeWidth = 1.1f;
            canvas.DrawCircle(_cx, _cy, radius, _addStroke);
        }

        // Iris blades over the lens
        float bladeR = rOut * 0.72f;
        var oval = new SKRect(_cx - bladeR, _cy - bladeR, _cx + bladeR, _cy + bladeR);
        _addStroke.Color = ArcTokens.Ignition.Fade(0.20f * m.Glow);
        _addStroke.StrokeWidth = 1f;
        for (int i = 0; i < 6; i++)
            canvas.DrawArc(oval, m.RotIris + i * 60f, 40f, false, _addStroke);
    }

    private void DrawHotCore(SKCanvas canvas, float radius, ReactorModel m)
    {
        float bloomR = radius * 7f;
        using (var shader = SKShader.CreateRadialGradient(
            new SKPoint(_cx, _cy), bloomR,
            new[]
            {
                ArcTokens.Ignition.Fade(0.80f * m.Glow),
                m.Tint.Fade(0.40f * m.Glow),
                ArcTokens.Arc.Fade(0.13f * m.Glow),
                SKColors.Transparent,
            },
            new[] { 0f, 0.08f, 0.30f, 1f }, SKShaderTileMode.Clamp))
        {
            _add.Shader = shader;
            canvas.DrawCircle(_cx, _cy, bloomR, _add);
            _add.Shader = null;
        }

        using (var shader = SKShader.CreateRadialGradient(
            new SKPoint(_cx, _cy), radius,
            new[]
            {
                SKColors.White.Fade(Math.Clamp(0.98f * m.Glow * 1.5f, 0f, 1f)),
                SKColors.White.Fade(0.80f * m.Glow),
                ArcTokens.Ignition.Fade(0.55f * m.Glow),
                m.Tint.Fade(0.06f * m.Glow),
            },
            new[] { 0f, 0.28f, 0.58f, 1f }, SKShaderTileMode.Clamp))
        {
            _add.Shader = shader;
            canvas.DrawCircle(_cx, _cy, radius, _add);
            _add.Shader = null;
        }

        // Anisotropic flare — the horizontal streak bright optics produce.
        float fw = radius * 6f, fh = radius * 0.10f;
        using (var shader = SKShader.CreateLinearGradient(
            new SKPoint(_cx - fw, _cy), new SKPoint(_cx + fw, _cy),
            new[] { SKColors.Transparent, ArcTokens.Ignition.Fade(0.16f * m.Glow), SKColors.Transparent },
            new[] { 0f, 0.5f, 1f }, SKShaderTileMode.Clamp))
        {
            _add.Shader = shader;
            canvas.DrawRect(new SKRect(_cx - fw, _cy - fh, _cx + fw, _cy + fh), _add);
            _add.Shader = null;
        }
    }

    private void DrawStatusArc(SKCanvas canvas, ReactorModel m, float cs)
    {
        float radius = R(ArcGeometry.StatusArc, cs);
        var oval = new SKRect(_cx - radius, _cy - radius, _cx + radius, _cy + radius);
        float sweep = ArcMotion.Lerp(30f, 96f, 0.5f + MathF.Sin(m.Time * 0.42f) * 0.5f);

        _stroke.Color = m.Tint.Fade(0.5f + 0.4f * m.Glow);
        _stroke.StrokeWidth = 2f;
        _stroke.StrokeCap = SKStrokeCap.Round;
        canvas.DrawArc(oval, 128f, sweep, false, _stroke);
        _stroke.StrokeCap = SKStrokeCap.Butt;
    }

    private void DrawSurgeAndRipples(SKCanvas canvas, ReactorModel m)
    {
        if (m.Surge > 0.001f)
        {
            float e = ArcMotion.CubicOut(m.Surge);
            _addStroke.Color = m.Tint.Fade((1f - m.Surge) * 0.42f);
            _addStroke.StrokeWidth = (1f - m.Surge) * 2.4f + 0.4f;
            canvas.DrawCircle(_cx, _cy, _r * ArcMotion.Lerp(1.3f, 3.4f, e), _addStroke);
        }

        foreach (float p in m.Ripples)
        {
            float e = ArcMotion.CubicOut(p);
            _stroke.Color = ArcTokens.Ignition.Fade((1f - p) * 0.45f);
            _stroke.StrokeWidth = (1f - p) * 2f + 0.3f;
            canvas.DrawCircle(_cx, _cy, _r * (1.4f + e * 2.2f), _stroke);
        }
    }

    /// <summary>
    /// Draws the orbital ring: connector hairline, outline icon, hover halo.
    /// Captions are not drawn here — they are MAUI labels positioned from
    /// <see cref="OrbitPosition"/>, because 8px text drawn into a canvas is
    /// unreadable next to the native font rasteriser.
    /// </summary>
    public void DrawOrbit(SKCanvas canvas, ArcItem[] items, ReactorModel m)
    {
        if (m.Open <= 0.01f || items.Length == 0) return;

        for (int i = 0; i < items.Length; i++)
        {
            float eased = ArcMotion.Stagger(m.Open, i, items.Length);
            if (eased <= 0.001f) continue;

            float a = ArcGeometry.ItemAngle(i, items.Length) * ArcMotion.Deg2Rad;
            float ca = MathF.Cos(a), sa = MathF.Sin(a);
            float rad = _r * ArcGeometry.Orbit * eased;
            float x = _cx + ca * rad, y = _cy + sa * rad;

            float hov = m.HoverIndex == i ? m.HoverAmount : 0f;
            float size = _r * ArcGeometry.IconSize
                       * ArcMotion.Lerp(0.55f, 1f, eased)
                       * ArcMotion.Lerp(1f, ArcGeometry.IconHoverScale, hov);
            var colour = hov > 0.05f
                ? ArcTokens.Lerp(ArcTokens.Arc, ArcTokens.Ignition, hov)
                : ArcTokens.Arc;
            float alpha = ArcMotion.Lerp(0.36f, 1f, hov) * eased;

            // Connector from the instrument ring out to the icon.
            _stroke.Color = ArcTokens.Arc.Fade((0.05f + 0.20f * hov) * eased);
            _stroke.StrokeWidth = 1f;
            float inner = _r * ArcGeometry.WedgeIn * 0.97f;
            canvas.DrawLine(_cx + ca * inner, _cy + sa * inner,
                            _cx + ca * (rad - size * 0.9f), _cy + sa * (rad - size * 0.9f), _stroke);

            // Icon — unit path scaled by the matrix, stroke divided back out.
            float box = size * 2f;
            canvas.Save();
            canvas.Translate(x, y);
            canvas.Scale(box, box);
            _stroke.Color = colour.Fade(alpha);
            _stroke.StrokeWidth = 1.15f / box;
            _stroke.StrokeJoin = SKStrokeJoin.Round;
            _stroke.StrokeCap = SKStrokeCap.Round;
            canvas.DrawPath(ArcIcons.Get(items[i].Icon), _stroke);
            canvas.Restore();
            _stroke.StrokeCap = SKStrokeCap.Butt;
            _stroke.StrokeJoin = SKStrokeJoin.Miter;

            if (hov > 0.05f)
            {
                _stroke.Color = ArcTokens.Plasma.Fade(0.30f * hov);
                _stroke.StrokeWidth = 1f;
                canvas.DrawCircle(x, y, size * 1.55f, _stroke);
            }
        }
    }

    /// <summary>
    /// Which orbital item sits under <paramref name="point"/>, or -1.
    ///
    /// The whole annular sector is the target, not the icon: a 31px glyph is
    /// far below the 44dp minimum, and the sector is what the hover highlight
    /// already shows the user.
    /// </summary>
    public int HitTest(SKPoint point, int itemCount, ReactorModel m)
    {
        if (m.Open < 0.4f || itemCount <= 0) return -1;

        float dx = point.X - _cx, dy = point.Y - _cy;
        float dist = MathF.Sqrt(dx * dx + dy * dy);
        if (dist < _r * ArcGeometry.WedgeIn || dist > _r * ArcGeometry.WedgeOut) return -1;

        float ang = MathF.Atan2(dy, dx) / ArcMotion.Deg2Rad;
        int best = -1;
        float bestDelta = 999f;
        for (int i = 0; i < itemCount; i++)
        {
            float target = ArcGeometry.ItemAngle(i, itemCount);
            // Shortest angular distance, always 0..180.
            float delta = MathF.Abs((((ang - target + 180f) % 360f) + 360f) % 360f - 180f);
            if (delta < bestDelta) { bestDelta = delta; best = i; }
        }
        return bestDelta <= 360f / itemCount / 2f ? best : -1;
    }

    /// <summary>True when the point falls on the reactor body itself.</summary>
    public bool HitsCore(SKPoint point, ReactorModel m)
    {
        float dx = point.X - _cx, dy = point.Y - _cy;
        return MathF.Sqrt(dx * dx + dy * dy) <= _r * ArcGeometry.BezelOut * m.CoreScale * 1.05f;
    }

    /// <summary>
    /// Paints the chrome wordmark below the reactor.
    ///
    /// Call after <see cref="Render"/>. Kept separate because the identity
    /// block is composition, not reactor: a host that wants the reactor
    /// without the branding simply does not call this.
    /// </summary>
    public void DrawWordmark(SKCanvas canvas, string text, SKTypeface? typeface,
                             ReactorModel m)
    {
        float size = _r * ArcGeometry.WordmarkSize;
        float baseline = _cy + R(ArcGeometry.WordmarkOffset, m.CoreScale);

        _text.Typeface = typeface;
        _text.TextSize = size;
        _text.TextAlign = SKTextAlign.Center;

        // Glow pass first, tinted by the current state — the wordmark
        // breathes with the reactor rather than sitting on top of it.
        _textGlow.Typeface = typeface;
        _textGlow.TextSize = size;
        _textGlow.TextAlign = SKTextAlign.Center;
        _textGlow.Color = m.Tint.Fade(0.45f * m.Glow);
        canvas.DrawText(text, _cx, baseline, _textGlow);

        // The gradient spans the glyph band, not the canvas: anchoring it
        // to cap height and baseline is what keeps the specular horizon
        // sitting across the middle of the letters at any size.
        using var shader = SKShader.CreateLinearGradient(
            new SKPoint(0, baseline - size * 0.78f),
            new SKPoint(0, baseline + size * 0.22f),
            ArcTokens.ChromeRamp, ArcTokens.ChromeStops, SKShaderTileMode.Clamp);

        _text.Shader = shader;
        canvas.DrawText(text, _cx, baseline, _text);
        _text.Shader = null;
    }

    /// <summary>
    /// Paints the clock and greeting under the wordmark.
    ///
    /// Drawn on the canvas rather than composed as MAUI labels: every
    /// overlay anchored to the centre of the host Grid measured to zero and
    /// never appeared, while the canvas draws here reliably. At 0.30 R the
    /// clock is large enough that Skia's rasteriser is fine.
    /// </summary>
    public void DrawIdentity(SKCanvas canvas, string clock, string greeting,
                             SKTypeface? clockFace, SKTypeface? captionFace,
                             ReactorModel m)
    {
        float fade = m.Depth > 0 ? 0.30f : 1f;
        float cs = m.CoreScale;

        float clockSize = _r * 0.30f;
        float clockBaseline = _cy + R(ArcGeometry.ClockOffset, cs);
        _text.Typeface = clockFace;
        _text.TextSize = clockSize;
        _text.TextAlign = SKTextAlign.Center;
        _text.Shader = null;
        _text.Color = ArcTokens.InkHi.Fade(fade);
        canvas.DrawText(clock, _cx, clockBaseline, _text);

        float capSize = _r * 0.115f;
        _text.Typeface = captionFace;
        _text.TextSize = capSize;
        _text.Color = ArcTokens.InkLo.Fade(fade);
        canvas.DrawText(greeting, _cx, clockBaseline + capSize * 2.1f, _text);
    }

    /// <summary>
    /// The live caption — what was just heard, or what is being said.
    /// Sits low on the screen so it never competes with the reactor.
    /// </summary>
    public void DrawCaption(SKCanvas canvas, string text, SKTypeface? face, ReactorModel m)
    {
        float size = _r * 0.155f;
        float y = _cy + _r * 4.2f;

        _text.Typeface = face;
        _text.TextSize = size;
        _text.TextAlign = SKTextAlign.Center;
        _text.Shader = null;
        _text.Color = ArcTokens.InkHi;

        // Wrap by hand: SKPaint measures but does not break lines, and a long
        // reply spilling off both edges is worse than no caption at all.
        float maxWidth = _r * 11f;
        var words = text.Split(' ');
        var line = new StringBuilder();
        var lines = new List<string>();
        foreach (var word in words)
        {
            var candidate = line.Length == 0 ? word : line + " " + word;
            if (_text.MeasureText(candidate) > maxWidth && line.Length > 0)
            {
                lines.Add(line.ToString());
                line.Clear().Append(word);
            }
            else { line.Clear().Append(candidate); }
            if (lines.Count == 3) break;
        }
        if (line.Length > 0 && lines.Count < 3) lines.Add(line.ToString());

        for (int i = 0; i < lines.Count; i++)
            canvas.DrawText(lines[i], _cx, y + i * size * 1.5f, _text);
    }

    public void Dispose()
    {
        _fill.Dispose(); _stroke.Dispose(); _add.Dispose();
        _addStroke.Dispose(); _dash.Dispose();
        _text.Dispose(); _textGlow.Dispose();
    }
}
