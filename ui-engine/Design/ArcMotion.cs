namespace SextaFeira.UIEngine.Design;

/// <summary>
/// Motion curves, durations, and the approach rates that drive the reactor.
/// See docs/design-system/01-TOKENS.md §6.
/// </summary>
public static class ArcMotion
{
    public const float Deg2Rad = MathF.PI / 180f;
    public const float Tau = MathF.PI * 2f;

    // ── Durations (seconds) ─────────────────────────────────
    public const float DurInstant = 0.12f;
    public const float DurFast    = 0.22f;
    public const float DurBase    = 0.34f;
    public const float DurSlow    = 0.55f;
    public const float DurBoot    = 2.20f;

    // ── Approach rates for continuous reactor properties ────
    // Higher = snappier. These are not durations: the reactor never
    // "arrives" anywhere, it chases a target that keeps moving.
    public const float RateGlow       = 3.2f;
    public const float RateSpin       = 2.6f;
    public const float RateCoreScale  = 4.0f;
    public const float RateTint       = 3.0f;
    public const float RateOpen       = 5.5f;
    public const float RateHover      = 8.0f;
    public const float RateWedgeAngle = 11.0f;
    public const float RateProximity  = 6.0f;

    /// <summary>Longest frame the simulation will honour. Beyond this — a
    /// resumed app, a stalled thread — we clamp rather than let the reactor
    /// jump a full rotation.</summary>
    public const float MaxDelta = 0.05f;

    /// <summary>
    /// Frame-rate independent exponential approach. The workhorse of the
    /// whole system: absorbs a target change mid-flight with no
    /// discontinuity, which a duration-based animation cannot do without
    /// being cancelled and restarted.
    /// </summary>
    public static float Approach(float current, float target, float rate, float dt) =>
        current + (target - current) * (1f - MathF.Exp(-rate * dt));

    /// <summary>Approach along the shortest arc, in radians. Without this,
    /// moving the hover sector from item 12 to item 1 sweeps the long way.</summary>
    public static float ApproachAngle(float current, float target, float rate, float dt)
    {
        float diff = ((target - current + MathF.PI * 3f) % Tau) - MathF.PI;
        return current + diff * (1f - MathF.Exp(-rate * dt));
    }

    // ── Easing ──────────────────────────────────────────────
    public static float CubicOut(float t)  { t = Math.Clamp(t, 0f, 1f); return 1f - MathF.Pow(1f - t, 3f); }
    public static float CubicIn(float t)   { t = Math.Clamp(t, 0f, 1f); return t * t * t; }
    public static float QuintOut(float t)  { t = Math.Clamp(t, 0f, 1f); return 1f - MathF.Pow(1f - t, 5f); }

    /// <summary>Overshoot, for orbital entry and dialog appearance.</summary>
    public static float BackOut(float t)
    {
        t = Math.Clamp(t, 0f, 1f);
        const float c1 = 1.70158f, c3 = c1 + 1f;
        return 1f + c3 * MathF.Pow(t - 1f, 3f) + c1 * MathF.Pow(t - 1f, 2f);
    }

    public static float Lerp(float a, float b, float t) => a + (b - a) * t;

    /// <summary>
    /// Staggered entry for orbital item <paramref name="index"/> of
    /// <paramref name="count"/>. Each item lags the one before it by 18%
    /// of the total, so the ring unfurls rather than popping.
    /// </summary>
    public static float Stagger(float open, int index, int count)
    {
        if (count <= 0) return 0f;
        float t = Math.Clamp((open - index / (float)count * 0.18f) / 0.82f, 0f, 1f);
        return CubicOut(t);
    }
}
