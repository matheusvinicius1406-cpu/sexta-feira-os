using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Action service contract — mirrors Python ActionAdapter.
/// Dispatches commands to devices.
/// </summary>
public interface IActionService
{
    /// <summary>Dispatch an action to a device.</summary>
    Task<ActionResult> DispatchActionAsync(string device, string action, Dictionary<string, string>? parameters = null);
}
