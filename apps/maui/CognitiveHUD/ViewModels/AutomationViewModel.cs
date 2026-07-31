using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Models;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>
/// ViewModel for automation — workflow list, trigger, event display.
/// Mirrors Python AutomationAdapter in the C# layer.
/// </summary>
public partial class AutomationViewModel : ObservableObject
{
    private readonly IAutomationService _automationService;
    private readonly IEventBus _eventBus;

    public AutomationViewModel(IAutomationService automationService, IEventBus eventBus)
    {
        _automationService = automationService;
        _eventBus = eventBus;

        // Subscribe to automation events
        // Not async: the handler only logs. Marking it async without an await
        // makes it run synchronously anyway, just with a state machine and a
        // compiler warning attached.
        _eventBus.Subscribe("workflow.*", evt =>
        {
            if (evt.Data.TryGetValue("workflow_id", out var wfId))
            {
                var msg = evt.EventType switch
                {
                    "workflow.started" => $"⚡ Workflow {wfId} iniciado",
                    "workflow.completed" => $"✅ Workflow {wfId} concluído",
                    _ => $"📢 {evt.EventType}: {wfId}",
                };

                System.Diagnostics.Debug.WriteLine(msg);
            }
            return Task.CompletedTask;
        });
    }

    // ── Observable State ─────────────────────────────────

    [ObservableProperty]
    private ObservableCollection<WorkflowInfo> _workflows = new();

    [ObservableProperty]
    private WorkflowInfo? _selectedWorkflow;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _errorMessage;

    [ObservableProperty]
    private string? _lastTriggerResult;

    // ── Commands ─────────────────────────────────────────

    [RelayCommand]
    private async Task LoadWorkflowsAsync()
    {
        IsLoading = true;
        ErrorMessage = null;
        try
        {
            var list = await _automationService.ListWorkflowsAsync();
            Workflows.Clear();
            foreach (var wf in list)
                Workflows.Add(wf);
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao carregar workflows: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task TriggerWorkflowAsync(string workflowId)
    {
        IsLoading = true;
        ErrorMessage = null;
        try
        {
            var result = await _automationService.TriggerWorkflowAsync(workflowId);
            LastTriggerResult = result.Accepted
                ? $"Workflow {workflowId} acionado com sucesso"
                : $"Falha ao acionar workflow {workflowId}";
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao acionar workflow: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }
}
