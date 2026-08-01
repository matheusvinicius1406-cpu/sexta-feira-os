using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Automation Engine contract — mirrors Python AutomationEngine.
/// Manages Teia automations, event streaming, and device commands.
/// </summary>
public interface IAutomationEngine : IEngine
{
    Task<WorkflowResult> TriggerWorkflowAsync(string workflowId, Dictionary<string, string>? parameters = null);
    Task<IReadOnlyList<WorkflowInfo>> ListWorkflowsAsync();
}
