using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Action service — mirrors Python ActionAdapter.
/// Dispatches commands to devices via gRPC.
/// </summary>
public class ActionService : IActionService
{
    private readonly GrpcClient _grpc;
    private readonly IEventBus _eventBus;

    public ActionService(GrpcClient grpc, IEventBus eventBus)
    {
        _grpc = grpc;
        _eventBus = eventBus;
    }

    public async Task<ActionResult> DispatchActionAsync(string device, string action, Dictionary<string, string>? parameters = null)
    {
        var commandId = await _grpc.DispatchActionAsync(device, action, parameters);

        if (!string.IsNullOrEmpty(commandId))
        {
            await _eventBus.PublishAsync("action.dispatched", new Dictionary<string, object>
            {
                ["device"] = device, ["action"] = action, ["command_id"] = commandId,
            });
        }

        return new ActionResult(
            CommandId: commandId ?? "",
            Accepted: !string.IsNullOrEmpty(commandId));
    }
}
