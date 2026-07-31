namespace SextaFeira.UIEngine.Design;

/// <summary>
/// Every distance in the ARC system is a multiple of R, the core radius.
/// That is what makes the reactor resolution-independent: one clamp on R
/// and the whole assembly rescales correctly from a phone to an ultrawide.
///
/// See docs/design-system/01-TOKENS.md §5.
/// </summary>
public static class ArcGeometry
{
    // ── Base radius ─────────────────────────────────────────

    /// <summary>Fraction of the shorter viewport axis the core occupies.</summary>
    public const float CoreFraction = 0.105f;
    public const float CoreMin = 52f;
    public const float CoreMax = 104f;

    /// <summary>R for a given surface. All other values multiply this.</summary>
    public static float CoreRadius(float width, float height) =>
        Math.Clamp(Math.Min(width, height) * CoreFraction, CoreMin, CoreMax);

    // ── Reactor body (multiples of R) ───────────────────────
    public const float HotCore    = 0.26f;
    public const float LensOuter  = 0.56f;

    public const float PlateCIn   = 0.60f;
    public const float PlateCOut  = 0.78f;
    public const float PlateBIn   = 0.84f;
    public const float PlateBOut  = 1.06f;
    public const float PlateAIn   = 1.12f;
    public const float PlateAOut  = 1.36f;

    public const float BezelIn    = 1.38f;
    public const float BezelOut   = 1.58f;

    public const float StrutIn    = 0.52f;
    public const float StrutOut   = 1.34f;

    // ── HUD instrumentation ─────────────────────────────────
    public const float HudSegRing = 1.62f;
    public const float HudTicks   = 1.66f;
    public const float StatusArc  = 1.70f;
    public const float WedgeIn    = 1.78f;
    public const float Orbit      = 2.40f;
    public const float WedgeOut   = 3.05f;
    public const float Boundary   = 3.24f;

    // The identity block sits below the reactor, never inside it: the core
    // is the brightest region on screen and text there would be unreadable.
    /// <summary>Baseline of the J.A.R.V.I.S. wordmark, below the reactor.</summary>
    public const float WordmarkOffset = 2.02f;
    /// <summary>Baseline of the clock, below the wordmark.</summary>
    public const float ClockOffset = 2.62f;
    /// <summary>Wordmark cap height, as a multiple of R.</summary>
    public const float WordmarkSize = 0.42f;

    // ── Plate counts and gaps ───────────────────────────────
    public const int PlateACount = 12;  public const float PlateAGap = 4.5f;
    public const int PlateBCount = 8;   public const float PlateBGap = 6.0f;
    public const int PlateCCount = 16;  public const float PlateCGap = 5.0f;
    public const int StrutCount  = 8;
    public const int TickCount   = 72;  public const int TickEvery   = 6;
    public const int LensLayers  = 7;

    // ── Rotation rates, degrees per second ──────────────────
    // Adjacent assemblies never share a direction or a rate — that
    // mismatch is what reads as depth without any real 3D.
    public const float RateBezel  = -1.6f;
    public const float RatePlateA = +4.2f;
    public const float RatePlateB = -6.8f;
    public const float RatePlateC = +10.5f;
    public const float RateStrut  = -2.4f;
    public const float RateIris   = +3.0f;
    public const float RateHud    = +7.0f;
    public const float RateTicks  = -3.5f;
    public const float RateBound  = -1.15f;

    /// <summary>
    /// Specular sweep. Deliberately NOT multiplied by the state's spin
    /// factor: the metal keeps catching light even when the reactor is
    /// offline, so "nothing is ever completely still" holds without
    /// making a dead system look alive.
    /// </summary>
    public const float RateSpecular = +14.0f;

    // ── Orbital layout ──────────────────────────────────────
    public const float OrbitStartAngle = -90f;   // 12 o'clock
    public const float IconSize = 0.30f;         // × R
    public const float IconHoverScale = 1.22f;

    /// <summary>Fractional width of a hover sector — the 14% shortfall is the gap.</summary>
    public const float SectorSpanFactor = 0.86f;

    /// <summary>Angle of orbital item <paramref name="index"/> of <paramref name="count"/>, in degrees.</summary>
    public static float ItemAngle(int index, int count) =>
        OrbitStartAngle + 360f / count * index;
}
