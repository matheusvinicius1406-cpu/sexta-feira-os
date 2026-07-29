using Microsoft.Maui.Graphics;
using SextaFeira.UIEngine.Animation;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Controls;

/// <summary>
/// Animation state for the radial menu.
/// </summary>
public enum RadialMenuState
{
    Idle,
    Expanding,
    Collapsing,
    /// <summary>Collapsing → rebuilding → expanding (layer transition)</summary>
    Transitioning,
}

/// <summary>
/// A radial menu container that positions child items in an orbital layout
/// around a center point. Supports:
/// - Automatic even distribution of items
/// - Animated entry (expansion from center)
/// - Animated exit (collapse to center)
/// - Layer transitions (collapse → swap items → re-expand)
/// - Configurable start angle and spacing
/// - Background dimming overlay
/// - Connecting lines between center and items
/// </summary>
public class RadialMenu
{
    // ── Layout ─────────────────────────────────────────────
    public float CenterX { get; set; }
    public float CenterY { get; set; }
    public float OrbitRadius { get; set; } = 140f;
    public float StartAngle { get; set; } = -90f;
    public float ItemRadius { get; set; } = 32f;

    // ── Items ──────────────────────────────────────────────
    private readonly List<RadialMenuItem> _items = new();
    public IReadOnlyList<RadialMenuItem> Items => _items.AsReadOnly();

    // ── Animation ──────────────────────────────────────────
    public RadialMenuState State { get; private set; } = RadialMenuState.Idle;
    private float _animationProgress;
    private bool _isExpanded;

    /// <summary>Split point for transitions: 0.5 = collapse halfway then expand.</summary>
    private const float TransitionSplitPoint = 0.5f;

    // ── Transition support ─────────────────────────────────
    private List<RadialMenuItem>? _pendingItems;
    private Action? _onTransitionMidpoint;
    private bool _transitionPhaseSwapDone;

    // ── Overlay ────────────────────────────────────────────
    public bool ShowOverlay { get; set; } = true;
    public float OverlayOpacity { get; set; } = 0.5f;

    // ── Events ─────────────────────────────────────────────
    public event Action? OnExpanded;
    public event Action? OnCollapsed;
    /// <summary>Fired at the midpoint of a transition (after collapse, before expand).</summary>
    public event Action? OnTransitionMidpoint;
    public event Action<RadialMenuItem>? OnItemSelected;

    public RadialMenu(float centerX, float centerY)
    {
        CenterX = centerX;
        CenterY = centerY;
    }

    // ── Item management ────────────────────────────────────
    public void AddItem(RadialMenuItem item)
    {
        _items.Add(item);
        RecalculatePositions();
    }

    public void AddItems(IEnumerable<RadialMenuItem> items)
    {
        _items.AddRange(items);
        RecalculatePositions();
    }

    public void ClearItems()
    {
        _items.Clear();
    }

    public RadialMenuItem? GetItemAt(PointF point)
    {
        foreach (var item in _items)
        {
            if (!item.IsVisible || item.Opacity < 0.1f) continue;
            if (item.HitTest(point))
                return item;
        }
        return null;
    }

    public void RecalculatePositions()
    {
        if (_items.Count == 0) return;

        float angleStep = 360f / _items.Count;
        float adjustedOrbit = _items.Count <= 3
            ? OrbitRadius * 0.85f
            : OrbitRadius;

        for (int i = 0; i < _items.Count; i++)
        {
            var item = _items[i];
            item.Angle = StartAngle + angleStep * i;
            item.OrbitRadius = adjustedOrbit;
            item.Radius = ItemRadius;
            item.UpdateOrbitPosition(CenterX, CenterY);
        }
    }

    // ── Expand / Collapse ──────────────────────────────────
    public void Expand()
    {
        if (_isExpanded) return;
        if (State == RadialMenuState.Transitioning) return;

        _isExpanded = true;
        State = RadialMenuState.Expanding;
        _animationProgress = 0f;

        foreach (var item in _items)
        {
            item.State = HudNodeState.Entering;
            item.Opacity = 0f;
            item.Scale = 0.3f;
            item.CurrentOrbitRadius = 0f;
            item.CurrentAngle = item.Angle;
            item.IsVisible = true;
        }
    }

    public void Collapse()
    {
        if (!_isExpanded) return;
        if (State == RadialMenuState.Transitioning) return;

        _isExpanded = false;
        State = RadialMenuState.Collapsing;
        _animationProgress = 0f;

        foreach (var item in _items)
        {
            item.State = HudNodeState.Exiting;
        }
    }

    // ── Layer Transition (50/50 split) ─────────────────────
    /// <summary>
    /// Smooth layer transition: collapses current items halfway,
    /// swaps to new items, then expands the rest of the way.
    /// 50/50 split ensures fluid ~0.55s total feel.
    /// </summary>
    public void TransitionTo(IEnumerable<RadialMenuItem> newItems)
    {
        if (newItems == null) throw new ArgumentNullException(nameof(newItems));

        var itemsList = newItems.ToList();

        if (!_isExpanded)
        {
            _items.Clear();
            _items.AddRange(itemsList);
            RecalculatePositions();
            Expand();
            return;
        }

        _pendingItems = itemsList;
        State = RadialMenuState.Transitioning;
        _animationProgress = 0f;
        _transitionPhaseSwapDone = false;

        _onTransitionMidpoint = () =>
        {
            _items.Clear();
            _items.AddRange(itemsList);
            RecalculatePositions();

            foreach (var item in _items)
            {
                item.State = HudNodeState.Entering;
                item.Opacity = 0f;
                item.Scale = 0.3f;
                item.CurrentOrbitRadius = 0f;
                item.CurrentAngle = item.Angle;
                item.IsVisible = true;
            }

            OnTransitionMidpoint?.Invoke();
        };

        // Start collapse
        foreach (var item in _items)
        {
            item.State = HudNodeState.Exiting;
        }
    }

    // ── Frame update ───────────────────────────────────────
    public void Update(float deltaSeconds)
    {
        if (State == RadialMenuState.Idle) return;

        float speed = 2.4f; // Slightly faster for 50/50 split
        _animationProgress += deltaSeconds * speed;

        bool isTransition = State == RadialMenuState.Transitioning;

        // ── Transition: swap at 50% ─────────────────────────
        if (isTransition && !_transitionPhaseSwapDone && _animationProgress >= TransitionSplitPoint)
        {
            _transitionPhaseSwapDone = true;
            _onTransitionMidpoint?.Invoke();
            _onTransitionMidpoint = null;
            _pendingItems = null;
            _isExpanded = true;
            // Reset animation state so expand phase plays from 0
            State = RadialMenuState.Expanding;
            _animationProgress = 0f;
            // Ensure isTransition is recalculated — it's now Expanding, not Transitioning
            isTransition = false;
            // fall through to apply easing for the expand phase this frame
        }

        // ── Completion ──────────────────────────────────────
        if (_animationProgress >= 1f)
        {
            _animationProgress = 1f;

            if (State == RadialMenuState.Expanding)
            {
                State = RadialMenuState.Idle;
                foreach (var item in _items)
                    item.State = HudNodeState.Idle;
                OnExpanded?.Invoke();
                return;
            }
            else if (State == RadialMenuState.Collapsing)
            {
                State = RadialMenuState.Idle;
                foreach (var item in _items)
                {
                    item.State = HudNodeState.Idle;
                    item.IsVisible = false;
                }
                OnCollapsed?.Invoke();
                return;
            }
        }

        // ── Compute normalised progress for this phase ──────
        float phaseDuration = isTransition ? TransitionSplitPoint : 1f;
        float eased = EasingFunctions.ExpandOut(_animationProgress / phaseDuration);

        foreach (var item in _items)
        {
            bool isExpanding = State == RadialMenuState.Expanding
                || (isTransition && _transitionPhaseSwapDone);
            bool isCollapsing = State == RadialMenuState.Collapsing
                || (isTransition && !_transitionPhaseSwapDone);

            if (isExpanding)
            {
                item.CurrentOrbitRadius = OrbitRadius * eased;
                float opacityProgress = Math.Clamp(_animationProgress / (TransitionSplitPoint * 1.2f), 0f, 1f);
                item.Opacity = EasingFunctions.FadeIn(opacityProgress);
                item.Scale = 0.3f + 0.7f * eased;
            }
            else if (isCollapsing)
            {
                item.CurrentOrbitRadius = OrbitRadius * (1f - eased);
                float opacityProgress = 1f - Math.Clamp(_animationProgress / (TransitionSplitPoint * 0.8f), 0f, 1f);
                item.Opacity = EasingFunctions.FadeIn(opacityProgress);
                item.Scale = 1f - 0.7f * eased;
            }

            item.UpdateOrbitPosition(CenterX, CenterY);
        }
    }

    // ── Draw ────────────────────────────────────────────────
    public void Draw(ICanvas canvas, RectF bounds)
    {
        bool isAnimating = State != RadialMenuState.Idle;

        // ── Dimming overlay ─────────────────────────────────
        if (ShowOverlay && isAnimating)
        {
            float overlayAlpha = State switch
            {
                RadialMenuState.Expanding => _animationProgress * OverlayOpacity,
                RadialMenuState.Transitioning when !_transitionPhaseSwapDone
                    => _animationProgress / TransitionSplitPoint * OverlayOpacity,
                RadialMenuState.Transitioning
                    => (1f - (_animationProgress - TransitionSplitPoint) / TransitionSplitPoint) * OverlayOpacity,
                _ => (1f - _animationProgress) * OverlayOpacity,
            };

            if (overlayAlpha > 0f)
            {
                canvas.FillColor = Colors.Black.WithAlpha(overlayAlpha);
                canvas.FillRectangle(bounds);
            }
        }

        // ── Connecting lines ────────────────────────────────
        if (_isExpanded || isAnimating)
        {
            float lineAlpha = _isExpanded ? 0.15f : _animationProgress * 0.15f;
            if (lineAlpha > 0.01f)
            {
                canvas.StrokeColor = NeonColors.Primary.WithAlpha(lineAlpha);
                canvas.StrokeSize = 0.5f;
                canvas.StrokeDashPattern = new float[] { 3, 3 };

                foreach (var item in _items)
                {
                    if (item.IsVisible && item.Opacity > 0.1f)
                        canvas.DrawLine(CenterX, CenterY, item.X, item.Y);
                }

                canvas.StrokeDashPattern = null;
            }
        }

        // ── Items ───────────────────────────────────────────
        foreach (var item in _items)
        {
            if (!item.IsVisible || item.Opacity <= 0f) continue;
            canvas.Alpha = item.Opacity;
            item.Draw(canvas, bounds);
            canvas.Alpha = 1f;
        }
    }
}
