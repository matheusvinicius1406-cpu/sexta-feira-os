using System.ComponentModel;
using Microsoft.Maui.Graphics;

namespace SextaFeira.UIEngine.Base;

/// <summary>
/// Represents the current visual state of a HUD node.
/// </summary>
public enum HudNodeState
{
    /// <summary>Default state, minimal visual presence.</summary>
    Idle,
    /// <summary>User is hovering or focusing on this node.</summary>
    Hovered,
    /// <summary>Node is the active selection.</summary>
    Active,
    /// <summary>Node is expanding outward (e.g., opening a sub-menu).</summary>
    Expanding,
    /// <summary>Node is collapsing inward.</summary>
    Collapsing,
    /// <summary>Node is animating into view.</summary>
    Entering,
    /// <summary>Node is animating out of view.</summary>
    Exiting,
}

/// <summary>
/// Abstract base class for every HUD visual element in the Sexta-Feira OS.
/// Provides position, rotation, scale, opacity, and glow properties
/// with animation-friendly patterns (observable, value-object based).
/// </summary>
public abstract class HudNode : INotifyPropertyChanged
{
    // ── Position ────────────────────────────────────────────
    private PointF _position;
    public PointF Position
    {
        get => _position;
        set
        {
            _position = value;
            OnPropertyChanged();
        }
    }

    public float X
    {
        get => _position.X;
        set
        {
            _position.X = value;
            OnPropertyChanged();
        }
    }

    public float Y
    {
        get => _position.Y;
        set
        {
            _position.Y = value;
            OnPropertyChanged();
        }
    }

    // ── Transform ───────────────────────────────────────────
    private float _rotation;
    public float Rotation
    {
        get => _rotation;
        set
        {
            _rotation = value;
            OnPropertyChanged();
        }
    }

    private float _scale = 1f;
    public float Scale
    {
        get => _scale;
        set
        {
            _scale = Math.Clamp(value, 0f, 5f);
            OnPropertyChanged();
        }
    }

    private float _opacity = 1f;
    public float Opacity
    {
        get => _opacity;
        set
        {
            _opacity = Math.Clamp(value, 0f, 1f);
            OnPropertyChanged();
        }
    }

    // ── Size ────────────────────────────────────────────────
    private float _radius = 40f;
    public float Radius
    {
        get => _radius;
        set
        {
            _radius = Math.Max(1f, value);
            OnPropertyChanged();
        }
    }

    public float Diameter => Radius * 2f;

    // ── Visual ──────────────────────────────────────────────
    private Color _color = Colors.Cyan;
    public Color Color
    {
        get => _color;
        set
        {
            _color = value;
            OnPropertyChanged();
        }
    }

    private float _glowIntensity;
    public float GlowIntensity
    {
        get => _glowIntensity;
        set
        {
            _glowIntensity = Math.Clamp(value, 0f, 1f);
            OnPropertyChanged();
        }
    }

    private Color _glowColor;
    public Color GlowColor
    {
        get => _glowColor;
        set
        {
            _glowColor = value;
            OnPropertyChanged();
        }
    }

    // ── State ───────────────────────────────────────────────
    private HudNodeState _state = HudNodeState.Idle;
    public HudNodeState State
    {
        get => _state;
        set
        {
            if (_state != value)
            {
                var previous = _state;
                _state = value;
                OnStateChanged(previous, value);
                OnPropertyChanged();
            }
        }
    }

    // ── Metadata ────────────────────────────────────────────
    public string Id { get; }
    public string Label { get; set; }
    public bool IsVisible { get; set; } = true;
    public bool IsInteractive { get; set; } = true;
    public object? Tag { get; set; }

    // ── Child nodes (for hierarchical HUDs) ─────────────────
    private readonly List<HudNode> _children = new();
    public IReadOnlyList<HudNode> Children => _children.AsReadOnly();
    public HudNode? Parent { get; private set; }

    protected HudNode(string id, string label, float radius = 40f)
    {
        Id = id;
        Label = label;
        Radius = radius;
        Color = NeonColors.Primary;
        GlowColor = NeonColors.Glow;
    }

    // ── Child management ────────────────────────────────────
    public void AddChild(HudNode child)
    {
        child.Parent = this;
        _children.Add(child);
    }

    public bool RemoveChild(HudNode child) => _children.Remove(child);

    public void ClearChildren() => _children.Clear();

    // ── Hit testing ─────────────────────────────────────────
    public virtual bool HitTest(PointF point)
    {
        if (!IsVisible || !IsInteractive)
            return false;

        float dx = point.X - _position.X;
        float dy = point.Y - _position.Y;
        return dx * dx + dy * dy <= Radius * Radius;
    }

    // ── Drawing ─────────────────────────────────────────────
    public abstract void Draw(ICanvas canvas, RectF bounds);

    /// <summary>
    /// Draws the glow effect around this node using layered
    /// semitransparent circles (MAUI Graphics does not support
    /// radial gradient brushes on ICanvas.FillColor).
    /// </summary>
    protected void DrawGlow(ICanvas canvas)
    {
        if (_glowIntensity <= 0f) return;

        float baseGlowRadius = Radius * 2.5f;
        int layers = 4;

        for (int i = layers - 1; i >= 0; i--)
        {
            float t = (i + 1f) / layers;
            float layerRadius = baseGlowRadius * t;
            float layerAlpha = (_glowIntensity / layers) * (1f - t * 0.6f);

            if (layerAlpha <= 0f) continue;

            canvas.FillColor = _glowColor.WithAlpha(layerAlpha);
            canvas.FillCircle(_position.X, _position.Y, layerRadius);
        }
    }

    // ── State lifecycle ─────────────────────────────────────
    protected virtual void OnStateChanged(HudNodeState previous, HudNodeState current) { }

    // ── INotifyPropertyChanged ──────────────────────────────
    public event PropertyChangedEventHandler? PropertyChanged;

    protected void OnPropertyChanged([System.Runtime.CompilerServices.CallerMemberName] string? name = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }
}
