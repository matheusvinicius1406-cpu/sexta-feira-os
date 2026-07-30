namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// DecisionService — mirrors Python DecisionEngine.
/// Manages constrained decision-making with audit trail.
/// Currently a stub — real implementation when decision gRPC endpoints exist.
/// </summary>
public class DecisionService
{
    private readonly IEventBus _eventBus;

    public DecisionService(IEventBus eventBus)
    {
        _eventBus = eventBus;
    }
}
