using Grpc.Net.Client;
using Google.Protobuf.WellKnownTypes;
using SextaFeira.CognitiveHUD.Models;
using Av1 = Automation.V1;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// gRPC client for communicating with the Sexta-Feira cognitive core backend.
/// Wraps the three gRPC services: CognitiveCore, VoiceStream, and AutomationService.
/// </summary>
public class GrpcClient : IDisposable
{
    private readonly GrpcChannel _channel;
    private readonly CognitiveCore.V1.CognitiveCore.CognitiveCoreClient _cognitiveCore;
    private readonly Voice.V1.VoiceStream.VoiceStreamClient _voiceStream;
    private readonly Automation.V1.AutomationService.AutomationServiceClient _automation;
    private bool _disposed;

    public GrpcClient(string grpcEndpoint = "http://127.0.0.1:50051")
    {
        _channel = GrpcChannel.ForAddress(grpcEndpoint, new GrpcChannelOptions
        {
            MaxSendMessageSize = 50 * 1024 * 1024,
            MaxReceiveMessageSize = 50 * 1024 * 1024,
        });
        _cognitiveCore = new CognitiveCore.V1.CognitiveCore.CognitiveCoreClient(_channel);
        _voiceStream = new Voice.V1.VoiceStream.VoiceStreamClient(_channel);
        _automation = new Automation.V1.AutomationService.AutomationServiceClient(_channel);
    }

    // ─────────────────────────────────────────────────────
    //  COGNITIVE CORE
    // ─────────────────────────────────────────────────────

    public async Task<CognitiveCore.V1.HealthCheckResponse?> CheckHealthCoreAsync()
    {
        try { return await _cognitiveCore.CheckHealthAsync(new CognitiveCore.V1.HealthCheckRequest()); }
        catch { return null; }
    }

    public async IAsyncEnumerable<string> ChatStreamAsync(string message, string? conversationId = null)
    {
        var request = new CognitiveCore.V1.ChatRequest
        {
            Message = message, ConversationId = conversationId ?? "",
        };
        using var call = _cognitiveCore.Chat(request);
        await foreach (var response in call.ResponseStream.ReadAllAsync())
        {
            if (response.ContentCase == CognitiveCore.V1.ChatResponse.ContentOneofCase.TextChunk)
                yield return response.TextChunk;
        }
    }

    public async Task<CognitiveCore.V1.MemoryNode?> CreateMemoryAsync(string content, string? title = null, int kind = 0)
    {
        try
        {
            return await _cognitiveCore.CreateMemoryAsync(new CognitiveCore.V1.CreateMemoryRequest
            { Content = content, Title = title ?? "", Kind = (CognitiveCore.V1.MemoryKind)kind });
        }
        catch { return null; }
    }

    public async Task<CognitiveCore.V1.MemoryNode?> GetMemoryCoreAsync(string memoryId)
    {
        try { return await _cognitiveCore.GetMemoryAsync(new CognitiveCore.V1.GetMemoryRequest { Id = memoryId }); }
        catch { return null; }
    }

    public async Task<bool> DeleteMemoryCoreAsync(string memoryId)
    {
        try
        {
            var r = await _cognitiveCore.DeleteMemoryAsync(new CognitiveCore.V1.DeleteMemoryRequest { Id = memoryId });
            return r.Success;
        }
        catch { return false; }
    }

    public async Task<IReadOnlyList<CognitiveCore.V1.MemoryNode>> SearchMemoryAsync(string query, int limit = 10)
    {
        try
        {
            var response = await _cognitiveCore.SearchMemoryAsync(
                new CognitiveCore.V1.SearchMemoryRequest { Query = query, Limit = limit });
            return response.Results.ToList().AsReadOnly();
        }
        catch { return Array.Empty<CognitiveCore.V1.MemoryNode>(); }
    }

    public async Task<CognitiveCore.V1.MemoryLink?> LinkMemoriesCoreAsync(string sourceId, string targetId, string relation = "related")
    {
        try
        {
            var pbRel = relation.ToLowerInvariant() switch
            {
                "created_by" => CognitiveCore.V1.RelationType.CreatedBy,
                "mentions" => CognitiveCore.V1.RelationType.Mentions,
                "causes" => CognitiveCore.V1.RelationType.Causes,
                "depends_on" => CognitiveCore.V1.RelationType.DependsOn,
                "opposes" => CognitiveCore.V1.RelationType.Opposes,
                _ => CognitiveCore.V1.RelationType.Related,
            };
            return await _cognitiveCore.LinkMemoriesAsync(
                new CognitiveCore.V1.LinkMemoriesRequest { SourceId = sourceId, TargetId = targetId, Relation = pbRel });
        }
        catch { return null; }
    }

    public async Task<bool> UnlinkMemoriesCoreAsync(string linkId)
    {
        try
        {
            var r = await _cognitiveCore.UnlinkMemoriesAsync(
                new CognitiveCore.V1.UnlinkMemoriesRequest { LinkId = linkId });
            return r.Success;
        }
        catch { return false; }
    }

    public async Task<CognitiveCore.V1.NeighboursResponse?> GetNeighboursCoreAsync(string memoryId)
    {
        try
        {
            return await _cognitiveCore.GetNeighboursAsync(
                new CognitiveCore.V1.GetNeighboursRequest { MemoryId = memoryId });
        }
        catch { return null; }
    }

    public async Task<CognitiveCore.V1.MemoryGraph?> GetMemoryGraphAsync(int maxNodes = 50)
    {
        try
        {
            return await _cognitiveCore.GetMemoryGraphAsync(
                new CognitiveCore.V1.GetMemoryGraphRequest { MaxNodes = maxNodes });
        }
        catch { return null; }
    }

    public async Task<string?> DispatchActionAsync(string device, string action, Dictionary<string, string>? parameters = null)
    {
        try
        {
            var request = new CognitiveCore.V1.DispatchActionRequest { Device = device, Action = action };
            if (parameters is not null)
                foreach (var kvp in parameters) request.Params[kvp.Key] = kvp.Value;
            var response = await _cognitiveCore.DispatchActionAsync(request);
            return response.Accepted ? response.CommandId : null;
        }
        catch { return null; }
    }

    // ─────────────────────────────────────────────────────
    //  VOICE
    // ─────────────────────────────────────────────────────

    public async Task<Voice.V1.VoiceStatusResponse?> GetVoiceStatusCoreAsync()
    {
        try { return await _voiceStream.GetVoiceStatusAsync(new Voice.V1.VoiceStatusRequest()); }
        catch { return null; }
    }

    public async Task<Voice.V1.TranscribeResponse?> TranscribeAudioCoreAsync(byte[] audioBytes)
    {
        try
        {
            return await _voiceStream.TranscribeAudioAsync(
                new Voice.V1.TranscribeAudioRequest { AudioData = Google.Protobuf.ByteString.CopyFrom(audioBytes) });
        }
        catch { return null; }
    }

    public async Task<byte[]?> SpeakTextCoreAsync(string text)
    {
        try
        {
            var response = await _voiceStream.SpeakTextAsync(new Voice.V1.SpeakTextRequest { Text = text });
            return response.AudioData.ToByteArray();
        }
        catch { return null; }
    }

    public async Task<Voice.V1.VoiceChatResponse?> VoiceChatCoreAsync(byte[] audioBytes, bool speakReply = true)
    {
        try
        {
            return await _voiceStream.VoiceChatAsync(new Voice.V1.VoiceChatRequest
            {
                AudioData = Google.Protobuf.ByteString.CopyFrom(audioBytes),
                SpeakReply = speakReply,
            });
        }
        catch { return null; }
    }

    // ─────────────────────────────────────────────────────
    //  AUTOMATION
    // ─────────────────────────────────────────────────────

    public async Task<bool> TriggerWorkflowAsync(string workflowId, Dictionary<string, string>? parameters = null)
    {
        try
        {
            var request = new Av1.TriggerWorkflowRequest { WorkflowId = workflowId };
            if (parameters is not null)
                foreach (var kvp in parameters) request.Params[kvp.Key] = kvp.Value;
            var response = await _automation.TriggerWorkflowAsync(request);
            return response.Accepted;
        }
        catch { return false; }
    }

    public async Task<IReadOnlyList<WorkflowInfo>> ListWorkflowsCoreAsync()
    {
        try
        {
            var response = await _automation.ListWorkflowsAsync(new Av1.ListWorkflowsRequest());
            return response.Workflows.Select(w => new WorkflowInfo(w.Id, w.Name, w.Active)).ToList().AsReadOnly();
        }
        catch { return Array.Empty<WorkflowInfo>(); }
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _channel?.Dispose();
            _disposed = true;
        }
    }
}
