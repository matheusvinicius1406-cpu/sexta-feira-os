namespace SextaFeira.CognitiveHUD.Services;

/// <summary>Placeholder stub for PlanningEngine until real implementation.</summary>
public sealed class PlanningEngineStub : DefaultEngine, IPlanningEngine
{
    public PlanningEngineStub() : base("Planning") { }
}

/// <summary>Placeholder stub for LearningEngine until real implementation.</summary>
public sealed class LearningEngineStub : DefaultEngine, ILearningEngine
{
    public LearningEngineStub() : base("Learning") { }
}

/// <summary>Placeholder stub for DecisionEngine until real implementation.</summary>
public sealed class DecisionEngineStub : DefaultEngine, IDecisionEngine
{
    public DecisionEngineStub() : base("Decision") { }
}

/// <summary>Placeholder stub for WorldModelEngine until real implementation.</summary>
public sealed class WorldModelEngineStub : DefaultEngine, IWorldModelEngine
{
    public WorldModelEngineStub() : base("WorldModel") { }

    /// <summary>
    /// No world model is wired up yet, so there is no snapshot to report.
    /// Returning null rather than a zeroed WorldState keeps "not implemented"
    /// distinguishable from "implemented and empty" at the call site.
    /// </summary>
    public Task<WorldState?> GetStateAsync() => Task.FromResult<WorldState?>(null);
}

/// <summary>Placeholder stub for SchedulerEngine until real implementation.</summary>
public sealed class SchedulerEngineStub : DefaultEngine, ISchedulerEngine
{
    public SchedulerEngineStub() : base("Scheduler") { }
}
