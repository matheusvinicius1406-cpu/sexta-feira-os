using SkiaSharp;
using SextaFeira.UIEngine.Design;

namespace SextaFeira.UIEngine.Reactor;

/// <summary>
/// What the assistant is actually doing.
///
/// These are never set by a control. They arrive from real signals — a wake
/// word, a stream opening, a link dropping — and the reactor renders the
/// consequence. See docs/design-system/05-MOVIMENTO.md §1.
/// </summary>
public enum ReactorState
{
    /// <summary>Awake, nothing in flight.</summary>
    Idle,
    /// <summary>Capturing audio.</summary>
    Listening,
    /// <summary>Model or agent is working. Also used for background jobs.</summary>
    Thinking,
    /// <summary>Streaming a response.</summary>
    Speaking,
    /// <summary>Degraded but functional — latency, quota, partial failure.</summary>
    Warning,
    /// <summary>A request or the link failed.</summary>
    Error,
    /// <summary>No transport to the kernel.</summary>
    Offline,
    /// <summary>Long idle. Lowest power draw.</summary>
    Sleep,
}

/// <summary>The continuous targets a state asks the reactor to move toward.</summary>
/// <param name="Glow">Bloom, ambient nebula, light escaping the plate gaps. 0..1</param>
/// <param name="Spin">Multiplier on every plate, coil and HUD ring rate — but not the specular sweep.</param>
/// <param name="CoreScale">Scale of the whole reactor assembly.</param>
/// <param name="Tint">Accent the assembly interpolates toward, channel by channel.</param>
/// <param name="Caption">Text shown by the status chip.</param>
public readonly record struct ReactorTarget(
    float Glow, float Spin, float CoreScale, SKColor Tint, string Caption);

public static class ReactorStates
{
    private static readonly Dictionary<ReactorState, ReactorTarget> Map = new()
    {
        [ReactorState.Idle]      = new(0.62f, 1.00f, 1.00f, ArcTokens.Plasma,   "Standby"),
        [ReactorState.Listening] = new(1.00f, 1.45f, 1.10f, ArcTokens.Plasma,   "Listening"),
        [ReactorState.Thinking]  = new(0.84f, 3.60f, 0.94f, ArcTokens.Arc,      "Thinking"),
        [ReactorState.Speaking]  = new(1.00f, 1.20f, 1.06f, ArcTokens.Ignition, "Speaking"),
        [ReactorState.Warning]   = new(0.78f, 0.82f, 1.00f, ArcTokens.Caution,  "Warning"),
        [ReactorState.Error]     = new(0.92f, 0.28f, 0.88f, ArcTokens.Breach,   "Fault"),
        [ReactorState.Offline]   = new(0.14f, 0.12f, 0.78f, ArcTokens.Steel,    "Offline"),
        [ReactorState.Sleep]     = new(0.09f, 0.06f, 0.70f, ArcTokens.Steel,    "Sleep"),
    };

    public static ReactorTarget For(ReactorState state) => Map[state];
}
