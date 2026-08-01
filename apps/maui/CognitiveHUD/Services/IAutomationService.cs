using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Automation service contract — mirrors Python AutomationAdapter.
/// Manages Teia automations, event streaming, and device commands.
/// </summary>
public interface IAutomationService
{
    /// <summary>Run a Teia automation by its slug.</summary>
    Task<WorkflowResult> TriggerWorkflowAsync(string workflowId, Dictionary<string, string>? parameters = null);

    /// <summary>List available workflows.</summary>
    Task<IReadOnlyList<WorkflowInfo>> ListWorkflowsAsync();
}
