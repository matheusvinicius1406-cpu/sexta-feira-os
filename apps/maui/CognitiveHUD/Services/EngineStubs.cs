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
}

/// <summary>Placeholder stub for SchedulerEngine until real implementation.</summary>
public sealed class SchedulerEngineStub : DefaultEngine, ISchedulerEngine
{
    public SchedulerEngineStub() : base("Scheduler") { }
}
