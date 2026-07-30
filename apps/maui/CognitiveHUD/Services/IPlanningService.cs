namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Planning Service contract — mirrors Python PlanningEngine.
/// </summary>
public interface IPlanningService
{
    Task<bool> CreatePlanAsync(string objective);
}
