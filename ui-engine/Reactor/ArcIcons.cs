using SkiaSharp;
using SextaFeira.UIEngine.Design;

namespace SextaFeira.UIEngine.Reactor;

public enum ArcIconKind
{
    Hex, Layers, Nodes, Folder, Grid, Term, Globe, Shield, Wave, Signal, Chip, Gear,
}

/// <summary>
/// Outline icons for the orbital ring, built once in a unit box (-0.5..0.5)
/// and scaled by the canvas matrix at draw time. Stroke weight is divided
/// back out so it stays optically constant at every size.
/// </summary>
public static class ArcIcons
{
    private static readonly Dictionary<ArcIconKind, SKPath> Cache = new();

    public static SKPath Get(ArcIconKind kind)
    {
        if (Cache.TryGetValue(kind, out var cached)) return cached;
        var path = Build(kind);
        Cache[kind] = path;
        return path;
    }

    private static SKPath Build(ArcIconKind kind)
    {
        var p = new SKPath();
        void Line(float x1, float y1, float x2, float y2) { p.MoveTo(x1, y1); p.LineTo(x2, y2); }
        void Circle(float x, float y, float r) => p.AddCircle(x, y, r);
        void Rect(float x, float y, float w, float h) => p.AddRect(new SKRect(x, y, x + w, y + h));

        switch (kind)
        {
            case ArcIconKind.Hex:
                for (int i = 0; i < 6; i++)
                {
                    float a = (i * 60 - 30) * ArcMotion.Deg2Rad;
                    float x = MathF.Cos(a) * 0.5f, y = MathF.Sin(a) * 0.5f;
                    if (i == 0) p.MoveTo(x, y); else p.LineTo(x, y);
                }
                p.Close(); Circle(0, 0, 0.14f);
                break;

            case ArcIconKind.Layers:
                Line(-0.45f, -0.22f, 0.45f, -0.22f);
                Line(-0.45f, 0.02f, 0.45f, 0.02f);
                Line(-0.45f, 0.26f, 0.45f, 0.26f);
                break;

            case ArcIconKind.Nodes:
                Circle(0, -0.32f, 0.13f); Circle(-0.34f, 0.26f, 0.13f); Circle(0.34f, 0.26f, 0.13f);
                Line(-0.08f, -0.20f, -0.28f, 0.14f);
                Line(0.08f, -0.20f, 0.28f, 0.14f);
                Line(-0.20f, 0.30f, 0.20f, 0.30f);
                break;

            case ArcIconKind.Folder:
                p.MoveTo(-0.45f, 0.32f); p.LineTo(-0.45f, -0.24f); p.LineTo(-0.10f, -0.24f);
                p.LineTo(-0.01f, -0.10f); p.LineTo(0.45f, -0.10f); p.LineTo(0.45f, 0.32f); p.Close();
                break;

            case ArcIconKind.Grid:
                Rect(-0.42f, -0.42f, 0.36f, 0.36f); Rect(0.06f, -0.42f, 0.36f, 0.36f);
                Rect(-0.42f, 0.06f, 0.36f, 0.36f);  Rect(0.06f, 0.06f, 0.36f, 0.36f);
                break;

            case ArcIconKind.Term:
                Rect(-0.46f, -0.36f, 0.92f, 0.72f);
                Line(-0.26f, -0.12f, -0.08f, 0.02f);
                Line(-0.08f, 0.02f, -0.26f, 0.16f);
                Line(0.02f, 0.16f, 0.26f, 0.16f);
                break;

            case ArcIconKind.Globe:
                Circle(0, 0, 0.44f); Line(-0.44f, 0, 0.44f, 0);
                p.MoveTo(0, -0.44f); p.CubicTo(0.28f, -0.18f, 0.28f, 0.18f, 0, 0.44f);
                p.MoveTo(0, -0.44f); p.CubicTo(-0.28f, -0.18f, -0.28f, 0.18f, 0, 0.44f);
                break;

            case ArcIconKind.Shield:
                p.MoveTo(0, -0.44f); p.LineTo(0.38f, -0.26f); p.LineTo(0.38f, 0.08f);
                p.CubicTo(0.38f, 0.30f, 0.18f, 0.40f, 0, 0.46f);
                p.CubicTo(-0.18f, 0.40f, -0.38f, 0.30f, -0.38f, 0.08f);
                p.LineTo(-0.38f, -0.26f); p.Close();
                break;

            case ArcIconKind.Wave:
                Line(-0.36f, -0.12f, -0.36f, 0.12f);
                Line(-0.18f, -0.30f, -0.18f, 0.30f);
                Line(0f, -0.44f, 0f, 0.44f);
                Line(0.18f, -0.26f, 0.18f, 0.26f);
                Line(0.36f, -0.10f, 0.36f, 0.10f);
                break;

            case ArcIconKind.Signal:
                Circle(0, 0.26f, 0.07f);
                for (int i = 1; i <= 3; i++)
                {
                    float r = 0.15f + i * 0.13f;
                    p.AddArc(new SKRect(-r, 0.26f - r, r, 0.26f + r), 225f, 90f);
                }
                break;

            case ArcIconKind.Chip:
                Rect(-0.30f, -0.30f, 0.60f, 0.60f);
                foreach (float o in new[] { -0.16f, 0f, 0.16f })
                {
                    Line(o, -0.30f, o, -0.44f); Line(o, 0.30f, o, 0.44f);
                    Line(-0.30f, o, -0.44f, o); Line(0.30f, o, 0.44f, o);
                }
                break;

            case ArcIconKind.Gear:
                Circle(0, 0, 0.20f);
                for (int i = 0; i < 8; i++)
                {
                    float a = i * 45 * ArcMotion.Deg2Rad;
                    Line(MathF.Cos(a) * 0.30f, MathF.Sin(a) * 0.30f,
                         MathF.Cos(a) * 0.45f, MathF.Sin(a) * 0.45f);
                }
                break;
        }
        return p;
    }
}
