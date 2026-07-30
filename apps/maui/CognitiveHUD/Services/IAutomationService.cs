using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Automation service contract — mirrors Python AutomationAdapter.
/// Manages n8n workflows, event streaming, and device commands.
/// </summary>
public interface IAutomationService
{
    /// <summary>Trigger an n8n workflow.</summary>
    Task<WorkflowResult> TriggerWorkflowAsync(string workflowId, Dictionary<string, string>? parameters = null);

    /// <summary>List available workflows.</summary>
    Task<IReadOnlyList<WorkflowInfo>> ListWorkflowsAsync();
}
