namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// HudService — manages HUD state, mode transitions, and publishes HUD events.
/// Mirrors the architecture for radial HUD interaction.
/// </summary>
public class HudService
{
    private readonly IEventBus _eventBus;

    public HudService(IEventBus eventBus)
    {
        _eventBus = eventBus;
    }

    /// <summary>Current HUD mode.</summary>
    public HudMode CurrentMode { get; private set; } = HudMode.Closed;

    /// <summary>Open the HUD (core circle appears).</summary>
    public async Task OpenAsync()
    {
        CurrentMode = HudMode.Opened;
        await _eventBus.PublishAsync("hud.opened", new Dictionary<string, object>());
    }

    /// <summary>Close the HUD (collapse to core).</summary>
    public async Task CloseAsync()
    {
        CurrentMode = HudMode.Closed;
        await _eventBus.PublishAsync("hud.closed", new Dictionary<string, object>());
    }

    /// <summary>Open a specific panel/module in the HUD.</summary>
    public async Task OpenPanelAsync(string panelId)
    {
        CurrentMode = HudMode.PanelOpen;
        await _eventBus.PublishAsync("hud.panel_opened", new Dictionary<string, object>
        {
            ["panel_id"] = panelId,
        });
    }

    /// <summary>Close the current panel.</summary>
    public async Task ClosePanelAsync(string panelId)
    {
        CurrentMode = HudMode.Closed;
        await _eventBus.PublishAsync("hud.panel_closed", new Dictionary<string, object>
        {
            ["panel_id"] = panelId,
        });
    }
}

/// <summary>HUD visual mode states.</summary>
public enum HudMode
{
    Closed,
    Opened,
    PanelOpen,
    Transitioning,
}
