using Microsoft.Maui.Graphics;

namespace SextaFeira.UIEngine.Base;

/// <summary>
/// Centralized color palette for the Sexta-Feira OS Neon Dark theme.
/// All HUD components reference these constants for visual consistency.
/// </summary>
public static class NeonColors
{
    // ── Background ──────────────────────────────────────────
    public static readonly Color Background = Color.FromArgb("#0A0A12");
    public static readonly Color Surface = Color.FromArgb("#12121E");
    public static readonly Color SurfaceLight = Color.FromArgb("#1A1A2E");

    // ── Primary ─────────────────────────────────────────────
    public static readonly Color Primary = Color.FromArgb("#00E5FF");
    public static readonly Color PrimaryDim = Color.FromArgb("#0099AA");
    public static readonly Color PrimaryLight = Color.FromArgb("#66F0FF");

    // ── Secondary ───────────────────────────────────────────
    public static readonly Color Secondary = Color.FromArgb("#7C4DFF");
    public static readonly Color SecondaryDim = Color.FromArgb("#4A1FB8");
    public static readonly Color SecondaryLight = Color.FromArgb("#B388FF");

    // ── Accent ──────────────────────────────────────────────
    public static readonly Color Accent = Color.FromArgb("#FF6D00");
    public static readonly Color AccentDim = Color.FromArgb("#B24000");
    public static readonly Color AccentLight = Color.FromArgb("#FF9E40");

    // ── Status ──────────────────────────────────────────────
    public static readonly Color Success = Color.FromArgb("#00E676");
    public static readonly Color Warning = Color.FromArgb("#FFD600");
    public static readonly Color Error = Color.FromArgb("#FF1744");
    public static readonly Color Info = Color.FromArgb("#40C4FF");

    // ── Text ────────────────────────────────────────────────
    public static readonly Color TextPrimary = Color.FromArgb("#E0E0FF");
    public static readonly Color TextSecondary = Color.FromArgb("#8888AA");
    public static readonly Color TextDisabled = Color.FromArgb("#444466");

    // ── Glow ────────────────────────────────────────────────
    public static readonly Color Glow = Color.FromArgb("#00E5FF");
    public static readonly Color GlowSecondary = Color.FromArgb("#7C4DFF");

    // ── Module-specific ─────────────────────────────────────
    public static readonly Color ModuleIA = Color.FromArgb("#00E5FF");
    public static readonly Color ModuleMemory = Color.FromArgb("#7C4DFF");
    public static readonly Color ModuleAgenda = Color.FromArgb("#00E676");
    public static readonly Color ModuleLibrary = Color.FromArgb("#FFD600");
    public static readonly Color ModuleAutomation = Color.FromArgb("#FF6D00");
    public static readonly Color ModuleDevices = Color.FromArgb("#40C4FF");
    public static readonly Color ModuleSettings = Color.FromArgb("#8888AA");

    /// <summary>
    /// Returns the module color for a given module identifier.
    /// </summary>
    public static Color ForModule(string moduleId) => moduleId.ToLowerInvariant() switch
    {
        "ia" or "ai" => ModuleIA,
        "memoria" or "memory" => ModuleMemory,
        "agenda" => ModuleAgenda,
        "biblioteca" or "library" => ModuleLibrary,
        "automacoes" or "automation" => ModuleAutomation,
        "dispositivos" or "devices" => ModuleDevices,
        "configuracoes" or "settings" => ModuleSettings,
        _ => Primary,
    };
}
