using System.Text;
using Google.Protobuf;
using Grpc.Core;
using Grpc.Net.Client;
using SextaFeira.CognitiveHUD.Models;
using Cv1 = SextaFeira.Cognitive.V1;
using Vv1 = SextaFeira.Voice.V1;
using Av1 = SextaFeira.Automation.V1;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// One completed turn of the bidirectional voice stream.
///
/// The wire protocol has no unary voice RPCs — everything flows through
/// <c>StreamVoice</c>. This record is what a turn collapses to once the
/// server closes its side.
/// </summary>
/// <param name="Transcript">Speech-to-text of what the caller sent.</param>
/// <param name="Reply">Assistant text, if the turn produced one.</param>
/// <param name="Audio">Synthesised speech bytes, empty when TTS was not requested.</param>
/// <param name="ErrorCode">Set when the server reported a VOICE_EVENT_ERROR.</param>
public sealed record VoiceTurn(
    string Transcript,
    string Reply,
    byte[] Audio,
    string? ErrorCode = null,
    string? ErrorMessage = null);

/// <summary>What the voice subsystem can currently do.</summary>
public sealed record VoiceCapabilities(bool Enabled, bool SttAvailable, bool TtsAvailable);

/// <summary>
/// gRPC client for the Sexta-Feira cognitive core.
/// Wraps three services: CognitiveCore, VoiceStream and AutomationService.
/// </summary>
public class GrpcClient : IDisposable
{
    private readonly GrpcChannel _channel;
    private readonly Cv1.CognitiveCore.CognitiveCoreClient _cognitiveCore;
    private readonly Vv1.VoiceStream.VoiceStreamClient _voiceStream;
    private readonly Av1.AutomationService.AutomationServiceClient _automation;
    private bool _disposed;

    public GrpcClient(string grpcEndpoint = "http://127.0.0.1:50051")
    {
        _channel = GrpcChannel.ForAddress(grpcEndpoint, new GrpcChannelOptions
        {
            MaxSendMessageSize = 50 * 1024 * 1024,
            MaxReceiveMessageSize = 50 * 1024 * 1024,
        });
        _cognitiveCore = new Cv1.CognitiveCore.CognitiveCoreClient(_channel);
        _voiceStream = new Vv1.VoiceStream.VoiceStreamClient(_channel);
        _automation = new Av1.AutomationService.AutomationServiceClient(_channel);
    }

    // ─────────────────────────────────────────────────────
    //  COGNITIVE CORE
    // ─────────────────────────────────────────────────────

    public async Task<Cv1.HealthCheckResponse?> CheckHealthCoreAsync()
    {
        try { return await _cognitiveCore.CheckHealthAsync(new Cv1.HealthCheckRequest()); }
        catch (RpcException) { return null; }
    }

    public async IAsyncEnumerable<string> ChatStreamAsync(string message, string? conversationId = null)
    {
        var request = new Cv1.ChatRequest
        {
            Message = message,
            ConversationId = conversationId ?? "",
        };
        using var call = _cognitiveCore.Chat(request);
        await foreach (var response in call.ResponseStream.ReadAllAsync())
        {
            if (response.ContentCase == Cv1.ChatResponse.ContentOneofCase.TextChunk)
                yield return response.TextChunk;
        }
    }

    public async Task<Cv1.MemoryNode?> CreateMemoryAsync(string content, string? title = null, int kind = 0)
    {
        try
        {
            return await _cognitiveCore.CreateMemoryAsync(new Cv1.CreateMemoryRequest
            { Content = content, Title = title ?? "", Kind = (Cv1.MemoryKind)kind });
        }
        catch (RpcException) { return null; }
    }

    public async Task<Cv1.MemoryNode?> GetMemoryCoreAsync(string memoryId)
    {
        try { return await _cognitiveCore.GetMemoryAsync(new Cv1.GetMemoryRequest { Id = memoryId }); }
        catch (RpcException) { return null; }
    }

    public async Task<bool> DeleteMemoryCoreAsync(string memoryId)
    {
        try
        {
            var r = await _cognitiveCore.DeleteMemoryAsync(new Cv1.DeleteMemoryRequest { Id = memoryId });
            return r.Success;
        }
        catch (RpcException) { return false; }
    }

    public async Task<IReadOnlyList<Cv1.MemoryNode>> SearchMemoryAsync(string query, int limit = 10)
    {
        try
        {
            var response = await _cognitiveCore.SearchMemoryAsync(
                new Cv1.SearchMemoryRequest { Query = query, Limit = limit });
            return response.Results.ToList().AsReadOnly();
        }
        catch (RpcException) { return Array.Empty<Cv1.MemoryNode>(); }
    }

    public async Task<Cv1.MemoryLink?> LinkMemoriesCoreAsync(string sourceId, string targetId, string relation = "related")
    {
        try
        {
            var pbRel = relation.ToLowerInvariant() switch
            {
                "created_by" => Cv1.RelationType.RelationCreatedBy,
                "mentions" => Cv1.RelationType.RelationMentions,
                "causes" => Cv1.RelationType.RelationCauses,
                "depends_on" => Cv1.RelationType.RelationDependsOn,
                "opposes" => Cv1.RelationType.RelationOpposes,
                _ => Cv1.RelationType.RelationRelated,
            };
            return await _cognitiveCore.LinkMemoriesAsync(
                new Cv1.LinkMemoriesRequest { SourceId = sourceId, TargetId = targetId, Relation = pbRel });
        }
        catch (RpcException) { return null; }
    }

    public async Task<bool> UnlinkMemoriesCoreAsync(string linkId)
    {
        try
        {
            var r = await _cognitiveCore.UnlinkMemoriesAsync(
                new Cv1.UnlinkMemoriesRequest { LinkId = linkId });
            return r.Success;
        }
        catch (RpcException) { return false; }
    }

    public async Task<Cv1.NeighboursResponse?> GetNeighboursCoreAsync(string memoryId)
    {
        try
        {
            return await _cognitiveCore.GetNeighboursAsync(
                new Cv1.GetNeighboursRequest { MemoryId = memoryId });
        }
        catch (RpcException) { return null; }
    }

    public async Task<Cv1.MemoryGraph?> GetMemoryGraphAsync(int maxNodes = 50)
    {
        try
        {
            return await _cognitiveCore.GetMemoryGraphAsync(
                new Cv1.GetMemoryGraphRequest { MaxNodes = maxNodes });
        }
        catch (RpcException) { return null; }
    }

    public async Task<string?> DispatchActionAsync(string device, string action, Dictionary<string, string>? parameters = null)
    {
        try
        {
            var request = new Cv1.DispatchActionRequest { Device = device, Action = action };
            if (parameters is not null)
                foreach (var kvp in parameters) request.Params[kvp.Key] = kvp.Value;
            var response = await _cognitiveCore.DispatchActionAsync(request);
            return response.Accepted ? response.CommandId : null;
        }
        catch (RpcException) { return null; }
    }

    // ─────────────────────────────────────────────────────
    //  VOICE
    //
    //  voice_stream.proto exposes exactly one RPC — a full-duplex
    //  StreamVoice(stream VoicePacket) → stream VoicePacket. There are no
    //  unary Transcribe/Speak/Status calls, so each of the operations
    //  below is one open-write-drain turn over that stream.
    // ─────────────────────────────────────────────────────

    private const int SampleRateHz = 16000;

    /// <summary>
    /// Runs a single voice turn: opens the duplex stream, sends a session
    /// config followed by <paramref name="outbound"/>, half-closes, then
    /// drains the server's side until it completes.
    /// </summary>
    private async Task<VoiceTurn?> RunVoiceTurnAsync(
        IEnumerable<Vv1.VoicePacket> outbound,
        bool wantTranscript,
        bool wantSpeech,
        string? conversationId,
        CancellationToken ct)
    {
        try
        {
            using var call = _voiceStream.StreamVoice(cancellationToken: ct);

            var config = new Vv1.VoiceSessionConfig
            {
                Codec = Vv1.AudioCodec.PcmS16Le,
                SampleRateHz = SampleRateHz,
                Channels = 1,
                EnableVad = true,
                EnableTranscript = wantTranscript,
                SpeakReply = wantSpeech,
            };
            if (conversationId is not null) config.ConversationId = conversationId;

            int sequence = 0;
            await call.RequestStream.WriteAsync(new Vv1.VoicePacket
            {
                Event = Vv1.VoiceEvent.Unspecified,
                SessionConfig = config,
                Sequence = sequence++,
            });

            foreach (var packet in outbound)
            {
                packet.Sequence = sequence++;
                await call.RequestStream.WriteAsync(packet);
            }

            // Half-close: tells the server no more audio is coming, which is
            // what makes it emit a final transcript instead of waiting on VAD.
            await call.RequestStream.WriteAsync(new Vv1.VoicePacket
            {
                Event = Vv1.VoiceEvent.EndOfSpeech,
                Sequence = sequence,
            });
            await call.RequestStream.CompleteAsync();

            // The proto carries user transcript and assistant reply on the
            // same packet type. Convention: the first transcript is the STT
            // of what we sent; everything after it is the reply.
            var transcripts = new List<string>();
            using var audio = new MemoryStream();
            string? errorCode = null, errorMessage = null;

            await foreach (var packet in call.ResponseStream.ReadAllAsync(ct))
            {
                switch (packet.PayloadCase)
                {
                    case Vv1.VoicePacket.PayloadOneofCase.Transcript:
                        if (!string.IsNullOrEmpty(packet.Transcript))
                            transcripts.Add(packet.Transcript);
                        break;

                    case Vv1.VoicePacket.PayloadOneofCase.AudioData:
                        packet.AudioData.WriteTo(audio);
                        break;

                    case Vv1.VoicePacket.PayloadOneofCase.Error:
                        errorCode = packet.Error.Code;
                        errorMessage = packet.Error.Message;
                        break;
                }

                if (packet.Event == Vv1.VoiceEvent.SessionEnd) break;
            }

            return new VoiceTurn(
                Transcript: transcripts.Count > 0 ? transcripts[0] : string.Empty,
                Reply: transcripts.Count > 1 ? string.Join(" ", transcripts.Skip(1)) : string.Empty,
                Audio: audio.ToArray(),
                ErrorCode: errorCode,
                ErrorMessage: errorMessage);
        }
        catch (RpcException) { return null; }
        catch (OperationCanceledException) { return null; }
    }

    private static Vv1.VoicePacket AudioPacket(byte[] audioBytes) => new()
    {
        Event = Vv1.VoiceEvent.AudioChunk,
        AudioData = ByteString.CopyFrom(audioBytes),
    };

    /// <summary>
    /// Probes voice availability.
    ///
    /// The wire protocol carries no capability breakdown, so STT and TTS
    /// availability both mirror link health rather than being reported
    /// separately. Add a capability RPC to voice_stream.proto if the two
    /// ever need to differ.
    /// </summary>
    public async Task<VoiceCapabilities> GetVoiceCapabilitiesAsync()
    {
        var health = await CheckHealthCoreAsync();
        bool up = health is not null;
        return new VoiceCapabilities(Enabled: up, SttAvailable: up, TtsAvailable: up);
    }

    /// <summary>Speech to text. Sends audio, requests a transcript, no TTS.</summary>
    public Task<VoiceTurn?> TranscribeAudioCoreAsync(byte[] audioBytes, CancellationToken ct = default) =>
        RunVoiceTurnAsync(new[] { AudioPacket(audioBytes) },
            wantTranscript: true, wantSpeech: false, conversationId: null, ct);

    /// <summary>Text to speech. Sends text, collects the synthesised audio.</summary>
    public async Task<byte[]?> SpeakTextCoreAsync(string text, CancellationToken ct = default)
    {
        var packet = new Vv1.VoicePacket
        {
            Event = Vv1.VoiceEvent.Transcript,
            Transcript = text,
        };
        var turn = await RunVoiceTurnAsync(new[] { packet },
            wantTranscript: false, wantSpeech: true, conversationId: null, ct);
        return turn?.Audio.Length > 0 ? turn.Audio : null;
    }

    /// <summary>Full loop: transcribe, think, optionally speak the reply.</summary>
    public Task<VoiceTurn?> VoiceChatCoreAsync(
        byte[] audioBytes, bool speakReply = true,
        string? conversationId = null, CancellationToken ct = default) =>
        RunVoiceTurnAsync(new[] { AudioPacket(audioBytes) },
            wantTranscript: true, wantSpeech: speakReply, conversationId, ct);

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
        catch (RpcException) { return false; }
    }

    public async Task<IReadOnlyList<WorkflowInfo>> ListWorkflowsCoreAsync()
    {
        try
        {
            var response = await _automation.ListWorkflowsAsync(new Av1.ListWorkflowsRequest());
            return response.Workflows
                .Select(w => new WorkflowInfo(w.Id, w.Name, w.Active))
                .ToList().AsReadOnly();
        }
        catch (RpcException) { return Array.Empty<WorkflowInfo>(); }
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _channel.Dispose();
            _disposed = true;
        }
        GC.SuppressFinalize(this);
    }
}
