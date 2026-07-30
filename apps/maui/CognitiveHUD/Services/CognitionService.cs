using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Cognition service — mirrors Python CognitionAdapter.
/// Manages chat streams, health checks, and brain state.
/// </summary>
public class CognitionService : ICognitionService
{
    private readonly GrpcClient _grpc;
    private readonly IEventBus _eventBus;

    public CognitionService(GrpcClient grpc, IEventBus eventBus)
    {
        _grpc = grpc;
        _eventBus = eventBus;
    }

    public async Task<HealthStatus> CheckHealthAsync()
    {
        var pb = await _grpc.CheckHealthCoreAsync();
        return new HealthStatus(
            IsOnline: pb is not null && (pb.Status == "ok" || pb.Status == "degraded"),
            Status: pb?.Status ?? "offline",
            Version: pb?.Version ?? "unknown",
            OllamaOnline: pb?.OllamaOnline ?? false,
            VoiceAvailable: pb?.VoiceAvailable ?? false,
            UptimeSeconds: pb?.UptimeSeconds ?? 0);
    }

    public async IAsyncEnumerable<string> ChatStreamAsync(string message, string? conversationId = null)
    {
        await _eventBus.PublishAsync("brain.thinking", new Dictionary<string, object>
        {
            ["message"] = message.Length > 200 ? message[..200] : message,
            ["conversation_id"] = conversationId ?? "",
        });

        var replyBuilder = new System.Text.StringBuilder();

        await foreach (var token in _grpc.ChatStreamAsync(message, conversationId))
        {
            replyBuilder.Append(token);
            yield return token;
        }

        var fullReply = replyBuilder.ToString();
        if (fullReply.Length > 0)
        {
            await _eventBus.PublishAsync("brain.reply", new Dictionary<string, object>
            {
                ["reply_length"] = fullReply.Length,
                ["conversation_id"] = conversationId ?? "",
            });
        }
    }

    public async Task<string> ChatAsync(string message, string? conversationId = null)
    {
        var reply = new System.Text.StringBuilder();
        await foreach (var token in ChatStreamAsync(message, conversationId))
        {
            reply.Append(token);
        }
        return reply.ToString();
    }
}
