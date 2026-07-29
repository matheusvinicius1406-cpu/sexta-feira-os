using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Animation;

/// <summary>
/// Types of transitions between HUD layers.
/// </summary>
public enum TransitionType
{
    /// <summary>Items expand outward from center.</summary>
    ExpandRadial,
    /// <summary>Items collapse inward to center.</summary>
    CollapseRadial,
    /// <summary>Current layer fades out while new layer fades in.</summary>
    CrossFade,
    /// <summary>Current layer shrinks while new layer grows behind it.</summary>
    ZoomOutIn,
    /// <summary>Current layer slides out as new layer slides in.</summary>
    SlideHorizontal,
}

/// <summary>
/// Coordinates complex multi-element transitions between HUD layers.
/// Manages the orchestration of fade, scale, position, and glow animations
/// for all elements in both the current and next layer simultaneously.
/// </summary>
public class TransitionController
{
    // ── Configuration ──────────────────────────────────────
    public float DefaultDuration { get; set; } = 0.5f;
    public float StaggerDelay { get; set; } = 0.04f; // Delay between each item
    public TransitionType DefaultType { get; set; } = TransitionType.ExpandRadial;

    // ── State ──────────────────────────────────────────────
    public bool IsTransitioning { get; private set; }
    private float _progress;
    private float _duration;
    private TransitionType _currentType;
    private readonly List<HudNode> _exitingNodes = new();
    private readonly List<HudNode> _enteringNodes = new();

    public event Action? OnTransitionStarted;
    public event Action? OnTransitionCompleted;

    // ── Start transition ───────────────────────────────────
    public void StartTransition(
        IReadOnlyList<HudNode> exitingNodes,
        IReadOnlyList<HudNode> enteringNodes,
        TransitionType? type = null,
        float? duration = null)
    {
        if (IsTransitioning) return;

        IsTransitioning = true;
        _progress = 0f;
        _duration = duration ?? DefaultDuration;
        _currentType = type ?? DefaultType;

        _exitingNodes.Clear();
        _exitingNodes.AddRange(exitingNodes);

        _enteringNodes.Clear();
        _enteringNodes.AddRange(enteringNodes);

        // Prepare entering nodes
        foreach (var node in _enteringNodes)
        {
            node.State = HudNodeState.Entering;
            node.Opacity = 0f;
            node.Scale = 0.3f;
            node.IsVisible = true;
        }

        // Prepare exiting nodes
        foreach (var node in _exitingNodes)
        {
            node.State = HudNodeState.Exiting;
        }

        OnTransitionStarted?.Invoke();
    }

    // ── Frame update ───────────────────────────────────────
    public void Update(float deltaSeconds)
    {
        if (!IsTransitioning) return;

        _progress += deltaSeconds / _duration;

        if (_progress >= 1f)
        {
            _progress = 1f;
            FinalizeTransition();
            return;
        }

        float eased = _currentType switch
        {
            TransitionType.ExpandRadial => EasingFunctions.BackOut(_progress),
            TransitionType.CollapseRadial => EasingFunctions.CubicIn(_progress),
            TransitionType.CrossFade => EasingFunctions.QuadInOut(_progress),
            TransitionType.ZoomOutIn => EasingFunctions.CubicInOut(_progress),
            TransitionType.SlideHorizontal => EasingFunctions.QuadOut(_progress),
            _ => EasingFunctions.QuadOut(_progress),
        };

        // ── Update exiting nodes ──────────────────────────
        for (int i = 0; i < _exitingNodes.Count; i++)
        {
            float itemDelay = i * StaggerDelay;
            float itemProgress = Math.Clamp((_progress - itemDelay / _duration) / (1f - itemDelay / _duration), 0f, 1f);

            if (itemProgress <= 0f) continue;

            float exitEased = _currentType switch
            {
                TransitionType.ExpandRadial => EasingFunctions.CubicIn(itemProgress),
                TransitionType.CrossFade => EasingFunctions.FadeIn(1f - itemProgress),
                _ => EasingFunctions.QuadIn(itemProgress),
            };

            _exitingNodes[i].Opacity = 1f - exitEased;
            _exitingNodes[i].Scale = 1f - exitEased * 0.7f;
        }

        // ── Update entering nodes ─────────────────────────
        for (int i = 0; i < _enteringNodes.Count; i++)
        {
            float itemDelay = i * StaggerDelay;
            float itemProgress = Math.Clamp((_progress - itemDelay / _duration) / (1f - itemDelay / _duration), 0f, 1f);

            if (itemProgress <= 0f)
            {
                _enteringNodes[i].Opacity = 0f;
                continue;
            }

            float enterEased = _currentType switch
            {
                TransitionType.ExpandRadial => EasingFunctions.ExpandOut(itemProgress),
                TransitionType.CrossFade => EasingFunctions.FadeIn(itemProgress),
                _ => EasingFunctions.BackOut(itemProgress),
            };

            _enteringNodes[i].Opacity = enterEased;
            _enteringNodes[i].Scale = 0.3f + 0.7f * enterEased;
        }
    }

    // ── Finalize ──────────────────────────────────────────
    private void FinalizeTransition()
    {
        foreach (var node in _exitingNodes)
        {
            node.Opacity = 0f;
            node.Scale = 0f;
            node.IsVisible = false;
            node.State = HudNodeState.Idle;
        }

        foreach (var node in _enteringNodes)
        {
            node.Opacity = 1f;
            node.Scale = 1f;
            node.State = HudNodeState.Idle;
        }

        _exitingNodes.Clear();
        _enteringNodes.Clear();
        IsTransitioning = false;

        OnTransitionCompleted?.Invoke();
    }

    /// <summary>
    /// Immediately completes any ongoing transition.
    /// </summary>
    public void SkipToEnd()
    {
        if (!IsTransitioning) return;
        _progress = 1f;
        FinalizeTransition();
    }
}
