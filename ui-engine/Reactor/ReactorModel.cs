using SkiaSharp;
using SextaFeira.UIEngine.Design;

namespace SextaFeira.UIEngine.Reactor;

/// <summary>
/// The reactor's continuous simulation. Holds no drawing code — it owns the
/// numbers, <see cref="ReactorRenderer"/> owns the pixels.
///
/// Nothing here snaps. Setting <see cref="State"/> only moves the targets;
/// every property then chases them at its own rate, so a state change that
/// lands mid-transition is absorbed rather than restarted.
/// </summary>
public sealed class ReactorModel
{
    // ── Driven by state ─────────────────────────────────────
    public ReactorState State { get; set; } = ReactorState.Idle;

    public float Glow      { get; private set; } = 0.62f;
    public float Spin      { get; private set; } = 1.00f;
    public float CoreScale { get; private set; } = 1.00f;
    public SKColor Tint    { get; private set; } = ArcTokens.Plasma;

    // ── Driven by navigation ────────────────────────────────
    /// <summary>0 = core only, 1 = orbital ring fully deployed.</summary>
    public float Open { get; private set; }
    public int Depth { get; set; }

    /// <summary>Module selected at depth 1, or -1. Drives what depth 2 shows.</summary>
    public int ActiveIndex { get; set; } = -1;

    /// <summary>Index of the hovered/focused orbital item, or -1.</summary>
    public int HoverIndex { get; set; } = -1;
    public int ItemCount { get; set; } = 12;
    public float HoverAmount { get; private set; }
    public float WedgeAngleRad { get; private set; }

    // ── Driven by input ─────────────────────────────────────
    /// <summary>Cursor closeness to the core, 0..1. Drives the "it feels you" reaction.</summary>
    public float Proximity { get; set; }

    // ── Transient effects ───────────────────────────────────
    /// <summary>Shockwave emitted on every state change. 1 → 0.</summary>
    public float Surge { get; private set; }
    private readonly List<float> _ripples = new(4);
    public IReadOnlyList<float> Ripples => _ripples;

    // ── Rotation accumulators (degrees) ─────────────────────
    public float RotSpecular, RotBezel, RotPlateA, RotPlateB, RotPlateC;
    public float RotStrut, RotIris, RotHud, RotTicks, RotBound;

    /// <summary>Seconds since start. Drives every breathing oscillator.</summary>
    public float Time { get; private set; }

    private ReactorState _lastState = ReactorState.Idle;

    public void Ripple() => _ripples.Add(0f);

    public void Update(float dt)
    {
        dt = MathF.Min(dt, ArcMotion.MaxDelta);
        Time += dt;

        // A state change is worth announcing visually, even to someone who
        // was not watching the status chip.
        if (State != _lastState) { _lastState = State; Surge = 1f; }

        var t = ReactorStates.For(State);

        Glow      = ArcMotion.Approach(Glow, t.Glow, ArcMotion.RateGlow, dt);
        Spin      = ArcMotion.Approach(Spin, t.Spin, ArcMotion.RateSpin, dt);
        CoreScale = ArcMotion.Approach(CoreScale,
                        t.CoreScale * (1f + Proximity * 0.04f),
                        ArcMotion.RateCoreScale, dt);

        Tint = new SKColor(
            (byte)ArcMotion.Approach(Tint.Red,   t.Tint.Red,   ArcMotion.RateTint, dt),
            (byte)ArcMotion.Approach(Tint.Green, t.Tint.Green, ArcMotion.RateTint, dt),
            (byte)ArcMotion.Approach(Tint.Blue,  t.Tint.Blue,  ArcMotion.RateTint, dt));

        Open = ArcMotion.Approach(Open, Depth > 0 ? 1f : 0f, ArcMotion.RateOpen, dt);

        HoverAmount = ArcMotion.Approach(HoverAmount,
                          HoverIndex >= 0 ? 1f : 0f, ArcMotion.RateHover, dt);

        if (HoverIndex >= 0 && ItemCount > 0)
        {
            float target = ArcGeometry.ItemAngle(HoverIndex, ItemCount) * ArcMotion.Deg2Rad;
            WedgeAngleRad = ArcMotion.ApproachAngle(
                WedgeAngleRad, target, ArcMotion.RateWedgeAngle, dt);
        }

        if (Surge > 0f) Surge = MathF.Max(0f, Surge - dt * 1.1f);

        for (int i = _ripples.Count - 1; i >= 0; i--)
        {
            _ripples[i] += dt * 1.5f;
            if (_ripples[i] >= 1f) _ripples.RemoveAt(i);
        }

        // Assemblies turn at their own rate and direction. The specular
        // sweep is the exception: it ignores Spin so the metal keeps
        // catching light even when the reactor is offline.
        RotSpecular += dt * ArcGeometry.RateSpecular * ArcMotion.Lerp(0.35f, 1f, Glow);
        RotBezel    += dt * ArcGeometry.RateBezel  * Spin;
        RotPlateA   += dt * ArcGeometry.RatePlateA * Spin;
        RotPlateB   += dt * ArcGeometry.RatePlateB * Spin;
        RotPlateC   += dt * ArcGeometry.RatePlateC * Spin;
        RotStrut    += dt * ArcGeometry.RateStrut  * Spin;
        RotIris     += dt * ArcGeometry.RateIris   * Spin;
        RotHud      += dt * ArcGeometry.RateHud    * Spin;
        RotTicks    += dt * ArcGeometry.RateTicks  * Spin;
        RotBound    += dt * ArcGeometry.RateBound  * Spin;
    }
}
