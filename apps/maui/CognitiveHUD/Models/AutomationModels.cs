namespace SextaFeira.CognitiveHUD.Models;

/// <summary>An n8n workflow descriptor.</summary>
public record WorkflowInfo(
    string Id,
    string Name,
    bool IsActive);

/// <summary>Trigger result from executing a workflow.</summary>
public record WorkflowResult(
    string ExecutionId,
    bool Accepted);

/// <summary>System event received from the event stream.</summary>
public record SystemEventPayload(
    string Type,
    string PayloadJson,
    DateTime Timestamp);

/// <summary>Command dispatched to a device.</summary>
public record DeviceCommand(
    string CommandId,
    string Action,
    Dictionary<string, string> Parameters,
    DateTime IssuedAt);

/// <summary>Result of a device command execution.</summary>
public record CommandResult(
    string CommandId,
    string DeviceId,
    bool Success,
    string? Error = null);
