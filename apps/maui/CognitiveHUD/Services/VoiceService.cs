using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Voice service — mirrors Python VoiceAdapter.
/// Manages STT (speech-to-text), TTS (text-to-speech), and full voice chat.
///
/// Every operation is one turn of the duplex StreamVoice RPC; see
/// <see cref="GrpcClient"/> for how a turn is assembled.
/// </summary>
public class VoiceService : IVoiceService, IVoiceEngine
{
    private readonly GrpcClient _grpc;
    private readonly IEventBus _eventBus;

    public VoiceService(GrpcClient grpc, IEventBus eventBus)
    {
        _grpc = grpc;
        _eventBus = eventBus;
    }

    public async Task<VoiceStatus> GetStatusAsync()
    {
        var caps = await _grpc.GetVoiceCapabilitiesAsync();
        return new VoiceStatus(
            IsEnabled: caps.Enabled,
            SttAvailable: caps.SttAvailable,
            TtsAvailable: caps.TtsAvailable);
    }

    public async Task<TranscriptResult?> TranscribeAsync(byte[] audioBytes)
    {
        var turn = await _grpc.TranscribeAudioCoreAsync(audioBytes);
        if (turn is null || string.IsNullOrEmpty(turn.Transcript))
            return null;

        await _eventBus.PublishAsync("voice.heard", new Dictionary<string, object>
        {
            ["transcript"] = Preview(turn.Transcript),
        });

        return new TranscriptResult(Text: turn.Transcript);
    }

    public async Task<byte[]?> SpeakAsync(string text)
    {
        await _eventBus.PublishAsync("voice.speaking", new Dictionary<string, object>
        {
            ["text_length"] = text.Length,
            ["text_preview"] = Preview(text),
        });

        return await _grpc.SpeakTextCoreAsync(text);
    }

    public async Task<VoiceChatResult?> VoiceChatAsync(byte[] audioBytes, bool speakReply = true)
    {
        var turn = await _grpc.VoiceChatCoreAsync(audioBytes, speakReply);
        if (turn is null) return null;

        return new VoiceChatResult(
            Transcript: turn.Transcript,
            Reply: turn.Reply,
            // The stream returns raw codec bytes; the domain model carries
            // them base64-encoded so callers can hand them straight to a
            // player or persist them as text.
            AudioWavBase64: turn.Audio.Length > 0 ? Convert.ToBase64String(turn.Audio) : null,
            ConversationId: null);
    }

    private static string Preview(string text) =>
        text.Length > 200 ? text[..200] : text;

    // ── IEngine ─────────────────────────────────────────────
    public string Name => "Voice";

    public Task InitializeAsync() => Task.CompletedTask;

    public async Task<bool> HealthAsync() =>
        Available = await _grpc.CheckHealthCoreAsync() is not null;

    public Task ShutdownAsync() => Task.CompletedTask;

    /// <summary>True once a health probe has succeeded.</summary>
    public bool Available { get; private set; }
}
