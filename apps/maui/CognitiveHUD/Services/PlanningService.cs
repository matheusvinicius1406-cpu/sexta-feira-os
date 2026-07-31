namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// PlanningService — mirrors Python PlanningEngine.
/// Manages goal-oriented plans, tasks, and objectives.
/// Currently a stub — real implementation when planning gRPC endpoints exist.
/// </summary>
public class PlanningService : IPlanningService
{
    private readonly IEventBus _eventBus;

    public PlanningService(IEventBus eventBus)
    {
        _eventBus = eventBus;
    }

    /// <summary>Placeholder for plan creation.</summary>
    public Task<bool> CreatePlanAsync(string objective)
    {
        System.Diagnostics.Debug.WriteLine($"[PlanningService] CreatePlan: {objective}");
        return Task.FromResult(true);
    }
}
