namespace SextaFeira.UIEngine.Animation;

/// <summary>
/// Stateless easing functions for smooth HUD animations.
/// All functions take a normalized progress value [0..1] and return
/// the eased value (usually also [0..1]).
/// 
/// Designed to be used with AnimationController and TransitionController.
/// </summary>
public static class EasingFunctions
{
    // ── Linear ─────────────────────────────────────────────
    public static float Linear(float t) => t;

    // ── Quad ───────────────────────────────────────────────
    public static float QuadIn(float t) => t * t;
    public static float QuadOut(float t) => 1f - (1f - t) * (1f - t);
    public static float QuadInOut(float t) =>
        t < 0.5f ? 2f * t * t : 1f - MathF.Pow(-2f * t + 2f, 2f) / 2f;

    // ── Cubic ──────────────────────────────────────────────
    public static float CubicIn(float t) => t * t * t;
    public static float CubicOut(float t) => 1f - MathF.Pow(1f - t, 3f);
    public static float CubicInOut(float t) =>
        t < 0.5f ? 4f * t * t * t : 1f - MathF.Pow(-2f * t + 2f, 3f) / 2f;

    // ── Elastic ────────────────────────────────────────────
    public static float ElasticOut(float t)
    {
        if (t <= 0f || t >= 1f) return t;
        float c4 = 2f * MathF.PI / 3f;
        return MathF.Pow(2f, -10f * t) * MathF.Sin((t * 10f - 0.75f) * c4) + 1f;
    }

    public static float ElasticIn(float t)
    {
        if (t <= 0f || t >= 1f) return t;
        float c4 = 2f * MathF.PI / 3f;
        return -MathF.Pow(2f, 10f * t - 10f) * MathF.Sin((t * 10f - 10.75f) * c4);
    }

    // ── Bounce ─────────────────────────────────────────────
    public static float BounceOut(float t)
    {
        const float n1 = 7.5625f;
        const float d1 = 2.75f;

        if (t < 1f / d1)       return n1 * t * t;
        else if (t < 2f / d1)  return n1 * (t -= 1.5f / d1) * t + 0.75f;
        else if (t < 2.5f / d1) return n1 * (t -= 2.25f / d1) * t + 0.9375f;
        else                    return n1 * (t -= 2.625f / d1) * t + 0.984375f;
    }

    public static float BounceIn(float t) => 1f - BounceOut(1f - t);

    // ── Back (overshoot) ───────────────────────────────────
    public static float BackOut(float t)
    {
        const float c1 = 1.70158f;
        const float c3 = c1 + 1f;
        return 1f + c3 * MathF.Pow(t - 1f, 3f) + c1 * MathF.Pow(t - 1f, 2f);
    }

    public static float BackIn(float t)
    {
        const float c1 = 1.70158f;
        const float c3 = c1 + 1f;
        return c3 * t * t * t - c1 * t * t;
    }

    // ── Radial Navigation Specific ─────────────────────────
    /// <summary>
    /// For expand animations: items emerge from center with slight overshoot.
    /// </summary>
    public static float ExpandOut(float t) => BackOut(t);

    /// <summary>
    /// For collapse animations: items shrink into center with ease.
    /// </summary>
    public static float CollapseIn(float t) => QuadIn(t);

    /// <summary>
    /// For fade transitions: smooth fade with slight cubic curve.
    /// </summary>
    public static float FadeIn(float t) => CubicOut(t);

    /// <summary>
    /// For pulse animations: smooth wave oscillation.
    /// </summary>
    public static float Pulse(float t) => MathF.Sin(t * MathF.PI * 2f);

    /// <summary>
    /// Spring-like overshoot for selection feedback.
    /// </summary>
    public static float Spring(float t) => ElasticOut(t) * 0.8f + 0.2f;
}
