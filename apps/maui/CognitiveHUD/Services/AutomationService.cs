using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Automation service — mirrors Python AutomationAdapter.
/// Manages n8n workflows, event streaming, and device commands.
/// </summary>
public class AutomationService : IAutomationService
{
    private readonly GrpcClient _grpc;

    public AutomationService(GrpcClient grpc)
    {
        _grpc = grpc;
    }

    public async Task<WorkflowResult> TriggerWorkflowAsync(string workflowId, Dictionary<string, string>? parameters = null)
    {
        var accepted = await _grpc.TriggerWorkflowAsync(workflowId, parameters);
        return new WorkflowResult(ExecutionId: "", Accepted: accepted);
    }

    public async Task<IReadOnlyList<WorkflowInfo>> ListWorkflowsAsync()
    {
        return await _grpc.ListWorkflowsCoreAsync();
    }
}
