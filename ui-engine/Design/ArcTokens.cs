using SkiaSharp;

namespace SextaFeira.UIEngine.Design;

/// <summary>
/// ARC Design System — the single source of truth for every colour the
/// reactor canvas paints.
///
/// Mirrored by <c>apps/maui/CognitiveHUD/Resources/Styles/Arc.Colors.xaml</c>,
/// which serves the MAUI control tree. The two files must never diverge —
/// see docs/design-system/07-CHECKLISTS.md §3.3 for the test that enforces it.
/// </summary>
public static class ArcTokens
{
    // ── Ground ──────────────────────────────────────────────
    // Neutrals biased toward the accent hue. A pure grey would read as
    // unconsidered; #000000 would read as "off", not as void.
    public static readonly SKColor Void     = SKColor.Parse("#000308");
    public static readonly SKColor Abyss    = SKColor.Parse("#060A12");
    public static readonly SKColor Graphite = SKColor.Parse("#0E1520");
    public static readonly SKColor Slate    = SKColor.Parse("#16202E");
    public static readonly SKColor Steel    = SKColor.Parse("#2A3A4E");

    // ── Accent ──────────────────────────────────────────────
    public static readonly SKColor Arc      = SKColor.Parse("#2E7DFF");
    public static readonly SKColor ArcDeep  = SKColor.Parse("#0B47B8");
    public static readonly SKColor Plasma   = SKColor.Parse("#35D6FF");
    public static readonly SKColor Ignition = SKColor.Parse("#C9F4FF");

    // ── Semantic — state, never decoration ──────────────────
    public static readonly SKColor Vital    = SKColor.Parse("#2EE6A8");
    public static readonly SKColor Caution  = SKColor.Parse("#FFB23D");
    public static readonly SKColor Breach   = SKColor.Parse("#FF4D6A");

    // ── Ink — hierarchy by luminance, not hue ───────────────
    // Contrast measured against Void by the WCAG 2.1 relative-luminance
    // formula. InkLo sits at 0.66 alpha because that is the lowest value
    // clearing 4.5:1 — 0.42 measured 2.48:1 and failed.
    public static readonly SKColor InkHi    = SKColor.Parse("#E9F4FF").WithAlpha(240); // 16.27:1
    public static readonly SKColor Ink      = SKColor.Parse("#C8DBF0").WithAlpha(184); //  7.61:1
    public static readonly SKColor InkLo    = SKColor.Parse("#A0B8D4").WithAlpha(168); //  4.73:1
    public static readonly SKColor InkGhost = SKColor.Parse("#8CA8C8").WithAlpha(51);  //  1.32:1 — non-text only

    // ── Metal ramp — the reactor's chrome, lit from upper-left ──
    // Pulled hard toward blue: this is not neutral steel, it is steel
    // drowning in the light of what it contains.
    public static readonly SKColor MetalDeep   = SKColor.Parse("#050A16");
    public static readonly SKColor MetalShadow = SKColor.Parse("#101E36");
    public static readonly SKColor MetalMid    = SKColor.Parse("#2D4468");
    public static readonly SKColor MetalLight  = SKColor.Parse("#6E9AD0");
    public static readonly SKColor MetalSpec   = SKColor.Parse("#D6ECFF");

    // ── Chrome ramp — the J.A.R.V.I.S. wordmark ─────────────
    // Vertical, not radial. The dark band at 50% is the specular
    // horizon: it is what separates polished metal from a blue
    // gradient, and removing it collapses the whole effect.
    public static readonly SKColor[] ChromeRamp =
    {
        SKColor.Parse("#F2FAFF"), SKColor.Parse("#BEDFF9"),
        SKColor.Parse("#639BD6"), SKColor.Parse("#143A66"),
        SKColor.Parse("#3F7EC2"), SKColor.Parse("#96C6EC"),
        SKColor.Parse("#E4F3FF"),
    };

    public static readonly float[] ChromeStops =
        { 0.00f, 0.20f, 0.40f, 0.50f, 0.58f, 0.76f, 1.00f };

    // ── Helpers ─────────────────────────────────────────────

    /// <summary>Applies a normalised alpha (0..1) on top of the token's own alpha.</summary>
    public static SKColor Fade(this SKColor c, float a) =>
        c.WithAlpha((byte)Math.Clamp(c.Alpha * a, 0f, 255f));

    /// <summary>Linear interpolation in sRGB. Good enough for tints; do not use for gradients.</summary>
    public static SKColor Lerp(SKColor a, SKColor b, float t)
    {
        t = Math.Clamp(t, 0f, 1f);
        return new SKColor(
            (byte)(a.Red   + (b.Red   - a.Red)   * t),
            (byte)(a.Green + (b.Green - a.Green) * t),
            (byte)(a.Blue  + (b.Blue  - a.Blue)  * t),
            (byte)(a.Alpha + (b.Alpha - a.Alpha) * t));
    }

    /// <summary>Every named colour, for the XAML-parity test.</summary>
    public static IReadOnlyDictionary<string, SKColor> AllColors { get; } =
        new Dictionary<string, SKColor>
        {
            [nameof(Void)] = Void,           [nameof(Abyss)] = Abyss,
            [nameof(Graphite)] = Graphite,   [nameof(Slate)] = Slate,
            [nameof(Steel)] = Steel,         [nameof(Arc)] = Arc,
            [nameof(ArcDeep)] = ArcDeep,     [nameof(Plasma)] = Plasma,
            [nameof(Ignition)] = Ignition,   [nameof(Vital)] = Vital,
            [nameof(Caution)] = Caution,     [nameof(Breach)] = Breach,
            [nameof(MetalDeep)] = MetalDeep, [nameof(MetalShadow)] = MetalShadow,
            [nameof(MetalMid)] = MetalMid,   [nameof(MetalLight)] = MetalLight,
            [nameof(MetalSpec)] = MetalSpec,
        };

    /// <summary>
    /// WCAG 2.1 contrast ratio. Used by the accessibility test to keep the
    /// ink ramp honest whenever a token is retuned.
    /// </summary>
    public static double Contrast(SKColor fg, SKColor bg)
    {
        // Composite fg over bg first — ink tokens carry alpha.
        float a = fg.Alpha / 255f;
        var flat = new SKColor(
            (byte)(fg.Red   * a + bg.Red   * (1 - a)),
            (byte)(fg.Green * a + bg.Green * (1 - a)),
            (byte)(fg.Blue  * a + bg.Blue  * (1 - a)));

        double l1 = Luminance(flat), l2 = Luminance(bg);
        (double hi, double lo) = l1 >= l2 ? (l1, l2) : (l2, l1);
        return (hi + 0.05) / (lo + 0.05);
    }

    private static double Luminance(SKColor c)
    {
        static double Channel(byte v)
        {
            double s = v / 255.0;
            return s <= 0.04045 ? s / 12.92 : Math.Pow((s + 0.055) / 1.055, 2.4);
        }
        return 0.2126 * Channel(c.Red) + 0.7152 * Channel(c.Green) + 0.0722 * Channel(c.Blue);
    }
}
