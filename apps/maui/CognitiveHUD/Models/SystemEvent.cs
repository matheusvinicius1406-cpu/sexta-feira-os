namespace SextaFeira.CognitiveHUD.Models;

/// <summary>
/// System event types — must mirror Python EventBus events exactly.
/// Complete list from FASE 6.2 specification.
/// </summary>
public static class SystemEventTypes
{
    // ── Memory ───────────────────────────────────────────
    public const string MemoryCreated = "memory.created";
    public const string MemoryUpdated = "memory.updated";
    public const string MemoryDeleted = "memory.deleted";
    public const string MemoryLinked = "memory.linked";
    public const string MemoryUnlinked = "memory.unlinked";
    public const string MemorySearched = "memory.searched";

    // ── Brain / Cognition ────────────────────────────────
    public const string BrainStarted = "brain.started";
    public const string BrainThinking = "brain.thinking";
    public const string BrainToolCall = "brain.tool_call";
    public const string BrainReasoning = "brain.reasoning";
    public const string BrainReply = "brain.reply";
    public const string BrainFinished = "brain.finished";

    // ── Voice ────────────────────────────────────────────
    public const string VoiceHeard = "voice.heard";
    public const string VoiceTranscribing = "voice.transcribing";
    public const string VoiceSpeaking = "voice.speaking";
    public const string VoiceFinished = "voice.finished";

    // ── Workflow / Automation ────────────────────────────
    public const string WorkflowStarted = "workflow.started";
    public const string WorkflowFinished = "workflow.finished";
    public const string WorkflowFailed = "workflow.failed";

    // ── Planning ─────────────────────────────────────────
    public const string PlanCreated = "plan.created";
    public const string PlanUpdated = "plan.updated";
    public const string PlanCompleted = "plan.completed";

    // ── Learning ─────────────────────────────────────────
    public const string LearningNewPattern = "learning.new_pattern";
    public const string LearningNewSkill = "learning.new_skill";
    public const string LearningConfidenceChanged = "learning.confidence_changed";

    // ── Decision ─────────────────────────────────────────
    public const string DecisionCreated = "decision.created";
    public const string DecisionExecuted = "decision.executed";

    // ── HUD ──────────────────────────────────────────────
    public const string HudOpened = "hud.opened";
    public const string HudClosed = "hud.closed";
    public const string HudPanelOpened = "hud.panel_opened";
    public const string HudPanelClosed = "hud.panel_closed";

    // ── System / Kernel ──────────────────────────────────
    public const string KernelStarted = "kernel.started";
    public const string KernelReady = "kernel.ready";
    public const string KernelShutdown = "kernel.shutdown";
}

/// <summary>
/// A system event with type and payload — mirrors Python's EventBus payload.
/// </summary>
public record SystemEvent(
    string EventType,
    IReadOnlyDictionary<string, object> Data,
    DateTime Timestamp) : IComparable<SystemEvent>
{
    public SystemEvent(string eventType, IReadOnlyDictionary<string, object> data)
        : this(eventType, data, DateTime.UtcNow) { }

    public int CompareTo(SystemEvent? other)
    {
        if (other is null) return 1;
        return Timestamp.CompareTo(other.Timestamp);
    }
}
