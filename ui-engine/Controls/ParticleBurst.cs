using Microsoft.Maui.Graphics;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Controls;

/// <summary>
/// A single particle in the burst effect.
/// </summary>
public struct Particle
{
    public float X, Y;
    public float VelocityX, VelocityY;
    public float Radius;
    public Color Color;
    public float Life;       // 0..1 (1 = alive, 0 = dead)
    public float DecayRate;
}

/// <summary>
/// Particle burst effect that plays during layer transitions.
/// Emits a burst of glowing particles from a center point when
/// navigating between depths.
/// 
/// Features:
/// - Radial burst from center
/// - Configurable count, speed, colors
/// - Deceleration/fade over lifetime
/// - Auto-removal when all particles die
/// </summary>
public class ParticleBurst
{
    private const int MaxParticles = 120;
    private readonly List<Particle> _particles = new(MaxParticles);
    private bool _isPlaying;

    // ── Configuration ───────────────────────────────────────
    private int _particleCount = 40;
    public int ParticleCount
    {
        get => _particleCount;
        set => _particleCount = Math.Clamp(value, 0, MaxParticles);
    }

    public float BaseSpeed { get; set; } = 200f;
    public float SpeedVariance { get; set; } = 100f;
    public float BaseRadius { get; set; } = 3f;
    public float RadiusVariance { get; set; } = 2f;
    public float LifeSpan { get; set; } = 0.8f;
    public float Gravity { get; set; } = 50f;

    private Color[] _colors = new[] { NeonColors.Primary, NeonColors.Secondary, NeonColors.Accent };
    public Color[]? Colors
    {
        get => _colors;
        set => _colors = (value is { Length: > 0 })
            ? value
            : new[] { NeonColors.Primary, NeonColors.Secondary, NeonColors.Accent };
    }

    // ── State ──────────────────────────────────────────────
    public bool IsPlaying => _isPlaying;
    public bool IsComplete => _particles.Count == 0;

    // ── Play the burst ─────────────────────────────────────
    public void Play(float centerX, float centerY)
    {
        _particles.Clear();
        _isPlaying = true;
        var rng = Random.Shared;

        var colors = _colors; // Already validated in setter

        int count = Math.Min(_particleCount, MaxParticles);

        for (int i = 0; i < count; i++)
        {
            float angle = rng.NextSingle() * MathF.PI * 2f;
            float speed = BaseSpeed + rng.NextSingle() * SpeedVariance;
            float radius = BaseRadius + rng.NextSingle() * RadiusVariance;
            float life = 0.7f + rng.NextSingle() * 0.3f;
            Color color = colors[rng.Next(colors.Length)];

            _particles.Add(new Particle
            {
                X = centerX,
                Y = centerY,
                VelocityX = MathF.Cos(angle) * speed,
                VelocityY = MathF.Sin(angle) * speed,
                Radius = radius,
                Color = color,
                Life = 1f,
                DecayRate = 1f / (LifeSpan * life),
            });
        }
    }

    // ── Frame update ───────────────────────────────────────
    public void Update(float deltaSeconds)
    {
        if (!_isPlaying) return;

        for (int i = _particles.Count - 1; i >= 0; i--)
        {
            var p = _particles[i];
            p.X += p.VelocityX * deltaSeconds;
            p.Y += p.VelocityY * deltaSeconds;
            p.VelocityX *= (1f - deltaSeconds * 0.8f);
            p.VelocityY *= (1f - deltaSeconds * 0.8f);
            p.VelocityY += Gravity * deltaSeconds;
            p.Life -= p.DecayRate * deltaSeconds;

            if (p.Life <= 0f)
                _particles.RemoveAt(i);
            else
                _particles[i] = p;
        }

        if (_particles.Count == 0)
            _isPlaying = false;
    }

    // ── Draw ────────────────────────────────────────────────
    public void Draw(ICanvas canvas)
    {
        if (!_isPlaying) return;

        foreach (var p in _particles)
        {
            float alpha = p.Life;
            float radius = p.Radius * (0.5f + 0.5f * p.Life);

            canvas.FillColor = p.Color.WithAlpha(alpha);
            canvas.FillCircle(p.X, p.Y, radius);

            if (alpha > 0.3f)
            {
                canvas.FillColor = p.Color.WithAlpha(alpha * 0.15f);
                canvas.FillCircle(p.X, p.Y, radius * 3f);
            }
        }
    }
}
