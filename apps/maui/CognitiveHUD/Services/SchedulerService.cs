namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// SchedulerService — mirrors Python SchedulerEngine.
/// Manages reminders, timed actions, and recurring tasks.
/// Currently a stub — real implementation when scheduler gRPC endpoints exist.
/// </summary>
public class SchedulerService : ISchedulerService
{
    private readonly IEventBus _eventBus;

    public SchedulerService(IEventBus eventBus)
    {
        _eventBus = eventBus;
    }
}
