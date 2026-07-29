using Microsoft.Maui.Graphics;
using SextaFeira.UIEngine.Animation;
using SextaFeira.UIEngine.Base;

namespace SextaFeira.UIEngine.Themes;

/// <summary>
/// Defines a complete visual theme for the Sexta-Feira HUD.
/// Each theme provides colors, fonts, sizes, glow parameters, and
/// animation preferences that the UI Engine components use for rendering.
/// </summary>
public interface ITheme
{
    // ── Identity ──────────────────────────────────────────
    string Name { get; }
    string Description { get; }

    // ── Backgrounds ───────────────────────────────────────
    Color Background { get; }
    Color Surface { get; }
    Color SurfaceLight { get; }

    // ── Core Colors ───────────────────────────────────────
    Color Primary { get; }
    Color PrimaryDim { get; }
    Color PrimaryLight { get; }
    Color Secondary { get; }
    Color Accent { get; }

    // ── Text ──────────────────────────────────────────────
    Color TextPrimary { get; }
    Color TextSecondary { get; }
    Color TextDisabled { get; }

    // ── Status ────────────────────────────────────────────
    Color Success { get; }
    Color Warning { get; }
    Color Error { get; }
    Color Info { get; }

    // ── Glow ──────────────────────────────────────────────
    Color GlowColor { get; }
    float GlowIntensity { get; }
    int GlowLayerCount { get; }

    // ── Core Circle ───────────────────────────────────────
    float CoreRadius { get; }
    float CorePulseSpeed { get; }
    float CorePulseAmount { get; }

    // ── Radial Menu ───────────────────────────────────────
    float MenuOrbitRadius { get; }
    float MenuItemRadius { get; }
    float MenuBackgroundOpacity { get; }
    bool MenuShowConnectingLines { get; }

    // ── Animation ─────────────────────────────────────────
    float AnimationDuration { get; }
    float AnimationStaggerDelay { get; }
    TransitionType DefaultTransition { get; }

    // ── Typography ────────────────────────────────────────
    string FontFamily { get; }
    float FontSizeSmall { get; }
    float FontSizeMedium { get; }
    float FontSizeLarge { get; }
    float FontSizeXLarge { get; }

    // ── Module colors ─────────────────────────────────────
    Color ColorForModule(string moduleId);
}
