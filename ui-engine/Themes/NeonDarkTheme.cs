using Microsoft.Maui.Graphics;
using SextaFeira.UIEngine.Animation;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Themes;

/// <summary>
/// The default Neon Dark theme — a cyberpunk/HUD-inspired dark theme
/// with cyan primary, purple secondary, and orange accent.
/// 
/// Inspired by: HUD futurista, Iron Man, holographic interfaces.
/// Identity própria: não copia nenhum produto existente.
/// </summary>
public class NeonDarkTheme : ITheme
{
    private static readonly Lazy<NeonDarkTheme> _instance = new(() => new NeonDarkTheme());
    public static NeonDarkTheme Instance => _instance.Value;

    private NeonDarkTheme() { }

    public string Name => "Neon Dark";
    public string Description => "Tema escuro futurista com tons neon ciano, roxo e laranja";

    // ── Backgrounds ───────────────────────────────────────
    public Color Background => Color.FromArgb("#0A0A12");
    public Color Surface => Color.FromArgb("#12121E");
    public Color SurfaceLight => Color.FromArgb("#1A1A2E");

    // ── Core Colors ──────────────────────────────────────
    public Color Primary => Color.FromArgb("#00E5FF");
    public Color PrimaryDim => Color.FromArgb("#0099AA");
    public Color PrimaryLight => Color.FromArgb("#66F0FF");
    public Color Secondary => Color.FromArgb("#7C4DFF");
    public Color Accent => Color.FromArgb("#FF6D00");

    // ── Text ─────────────────────────────────────────────
    public Color TextPrimary => Color.FromArgb("#E0E0FF");
    public Color TextSecondary => Color.FromArgb("#8888AA");
    public Color TextDisabled => Color.FromArgb("#444466");

    // ── Status ───────────────────────────────────────────
    public Color Success => Color.FromArgb("#00E676");
    public Color Warning => Color.FromArgb("#FFD600");
    public Color Error => Color.FromArgb("#FF1744");
    public Color Info => Color.FromArgb("#40C4FF");

    // ── Glow ─────────────────────────────────────────────
    public Color GlowColor => Color.FromArgb("#00E5FF");
    public float GlowIntensity => 0.5f;
    public int GlowLayerCount => 3;

    // ── Core Circle ──────────────────────────────────────
    public float CoreRadius => 60f;
    public float CorePulseSpeed => 1.5f;
    public float CorePulseAmount => 0.08f;

    // ── Radial Menu ──────────────────────────────────────
    public float MenuOrbitRadius => 150f;
    public float MenuItemRadius => 32f;
    public float MenuBackgroundOpacity => 0.5f;
    public bool MenuShowConnectingLines => true;

    // ── Animation ────────────────────────────────────────
    public float AnimationDuration => 0.5f;
    public float AnimationStaggerDelay => 0.04f;
    public TransitionType DefaultTransition => TransitionType.ExpandRadial;

    // ── Typography ───────────────────────────────────────
    public string FontFamily => "Courier New";
    public float FontSizeSmall => 9f;
    public float FontSizeMedium => 12f;
    public float FontSizeLarge => 16f;
    public float FontSizeXLarge => 22f;

    // ── Module colors ────────────────────────────────────
    public Color ColorForModule(string moduleId) => moduleId.ToLowerInvariant() switch
    {
        "ia" or "ai" => Primary,
        "memoria" or "memory" => Secondary,
        "agenda" => Success,
        "biblioteca" or "library" => Warning,
        "automacoes" or "automation" => Accent,
        "dispositivos" or "devices" => Info,
        "configuracoes" or "settings" => TextSecondary,
        _ => Primary,
    };
}
