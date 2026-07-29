namespace SextaFeira.UIEngine.Animation;

/// <summary>
/// Defines how an animation interpolates over time.
/// </summary>
public record struct AnimationDescriptor
{
    public string Id { get; init; }
    public float Duration { get; init; }
    public float Delay { get; init; }
    public Func<float, float> Easing { get; init; }
    public Action<float> OnUpdate { get; init; }
    public Action? OnComplete { get; init; }
    public bool Looping { get; init; }
    public bool AutoReverse { get; init; }
    public int LoopCount { get; init; } // 0 = infinite
}

/// <summary>
/// Runtime state of a single animation instance.
/// </summary>
internal class AnimationInstance
{
    public AnimationDescriptor Descriptor;
    public float Elapsed;
    public int CurrentLoop;
    public bool IsReversing;
    public bool IsComplete;
}

/// <summary>
/// Centralized animation controller for the Sexta-Feira HUD.
/// Manages multiple concurrent animations with pause/resume/cancel support.
/// All timing is relative (delta-based), not frame-based.
/// </summary>
public class AnimationController
{
    private readonly List<AnimationInstance> _activeAnimations = new();
    private readonly List<AnimationInstance> _pendingAnimations = new();
    private bool _paused;
    private float _globalSpeed = 1f;
    private readonly object _lock = new();

    // ── Properties ─────────────────────────────────────────
    public bool IsPaused => _paused;
    public float GlobalSpeed
    {
        get => _globalSpeed;
        set => _globalSpeed = Math.Max(0f, value);
    }
    public int ActiveCount => _activeAnimations.Count;

    // ── Create animation ───────────────────────────────────
    public string Animate(AnimationDescriptor descriptor)
    {
        lock (_lock)
        {
            var instance = new AnimationInstance
            {
                Descriptor = descriptor,
                Elapsed = -descriptor.Delay, // Negative = in delay phase
            };
            _activeAnimations.Add(instance);
            return descriptor.Id;
        }
    }

    /// <summary>
    /// Convenience: create a simple value animation.
    /// </summary>
    public string AnimateValue(
        string id,
        float duration,
        Action<float> onUpdate,
        Func<float, float>? easing = null,
        Action? onComplete = null,
        bool looping = false)
    {
        return Animate(new AnimationDescriptor
        {
            Id = id,
            Duration = duration,
            Easing = easing ?? EasingFunctions.QuadOut,
            OnUpdate = onUpdate,
            OnComplete = onComplete,
            Looping = looping,
        });
    }

    // ── Control ───────────────────────────────────────────
    public void Pause() => _paused = true;
    public void Resume() => _paused = false;

    public void Cancel(string id)
    {
        lock (_lock)
        {
            _activeAnimations.RemoveAll(a => a.Descriptor.Id == id);
        }
    }

    public void CancelAll()
    {
        lock (_lock)
        {
            _activeAnimations.Clear();
        }
    }

    public void Complete(string id)
    {
        lock (_lock)
        {
            var anim = _activeAnimations.Find(a => a.Descriptor.Id == id);
            if (anim != null)
            {
                anim.Descriptor.OnUpdate(1f);
                anim.Descriptor.OnComplete?.Invoke();
                _activeAnimations.Remove(anim);
            }
        }
    }

    // ── Frame update ───────────────────────────────────────
    public void Update(float deltaSeconds)
    {
        if (_paused || deltaSeconds <= 0f) return;

        float adjustedDelta = deltaSeconds * _globalSpeed;

        lock (_lock)
        {
            for (int i = _activeAnimations.Count - 1; i >= 0; i--)
            {
                var anim = _activeAnimations[i];

                // ── Delay phase ────────────────────────────
                if (anim.Elapsed < 0f)
                {
                    anim.Elapsed += adjustedDelta;
                    if (anim.Elapsed < 0f) continue;
                }

                // ── Active phase ───────────────────────────
                if (!anim.IsReversing)
                {
                    anim.Elapsed += adjustedDelta;
                }
                else
                {
                    anim.Elapsed -= adjustedDelta;
                }

                float progress = Math.Clamp(anim.Elapsed / anim.Descriptor.Duration, 0f, 1f);
                float eased = anim.Descriptor.Easing(progress);
                anim.Descriptor.OnUpdate(eased);

                // ── Completion / looping ───────────────────
                bool forwardComplete = !anim.IsReversing && anim.Elapsed >= anim.Descriptor.Duration;
                bool reverseComplete = anim.IsReversing && anim.Elapsed <= 0f;

                if (forwardComplete || reverseComplete)
                {
                    if (anim.Descriptor.Looping || anim.Descriptor.AutoReverse)
                    {
                        if (anim.Descriptor.AutoReverse)
                        {
                            anim.IsReversing = !anim.IsReversing;
                            // Clamp to bounds
                            anim.Elapsed = anim.IsReversing
                                ? anim.Descriptor.Duration
                                : 0f;
                        }

                        if (anim.Descriptor.Looping)
                        {
                            anim.Elapsed = 0f;
                            anim.CurrentLoop++;
                            if (anim.Descriptor.LoopCount > 0 &&
                                anim.CurrentLoop >= anim.Descriptor.LoopCount)
                            {
                                anim.Descriptor.OnComplete?.Invoke();
                                _activeAnimations.RemoveAt(i);
                            }
                        }
                    }
                    else
                    {
                        anim.Descriptor.OnUpdate(1f);
                        anim.Descriptor.OnComplete?.Invoke();
                        _activeAnimations.RemoveAt(i);
                    }
                }
            }
        }
    }
}
