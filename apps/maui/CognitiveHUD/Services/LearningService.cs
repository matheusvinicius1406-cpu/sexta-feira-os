namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// LearningService — mirrors Python LearningEngine.
/// Manages continuous learning, pattern recognition, and skill acquisition.
/// Currently a stub — real implementation when learning gRPC endpoints exist.
/// </summary>
public class LearningService
{
    private readonly IEventBus _eventBus;

    public LearningService(IEventBus eventBus)
    {
        _eventBus = eventBus;
    }
}
