using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Voice service — mirrors Python VoiceAdapter.
/// Manages STT (speech-to-text), TTS (text-to-speech), and full voice chat.
/// </summary>
public class VoiceService : IVoiceService
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
        var pb = await _grpc.GetVoiceStatusCoreAsync();
        return new VoiceStatus(
            IsEnabled: pb?.Enabled ?? false,
            SttAvailable: pb?.SttAvailable ?? false,
            TtsAvailable: pb?.TtsAvailable ?? false);
    }

    public async Task<TranscriptResult?> TranscribeAsync(byte[] audioBytes)
    {
        var pb = await _grpc.TranscribeAudioCoreAsync(audioBytes);
        if (pb is null || string.IsNullOrEmpty(pb.Text))
            return null;

        await _eventBus.PublishAsync("voice.heard", new Dictionary<string, object>
        {
            ["transcript"] = pb.Text.Length > 200 ? pb.Text[..200] : pb.Text,
        });

        return new TranscriptResult(Text: pb.Text);
    }

    public async Task<byte[]?> SpeakAsync(string text)
    {
        await _eventBus.PublishAsync("voice.speaking", new Dictionary<string, object>
        {
            ["text_length"] = text.Length,
            ["text_preview"] = text.Length > 200 ? text[..200] : text,
        });

        return await _grpc.SpeakTextCoreAsync(text);
    }

    public async Task<VoiceChatResult?> VoiceChatAsync(byte[] audioBytes, bool speakReply = true)
    {
        var pb = await _grpc.VoiceChatCoreAsync(audioBytes, speakReply);
        if (pb is null) return null;

        return new VoiceChatResult(
            Transcript: pb.Transcript,
            Reply: pb.Reply,
            AudioWavBase64: pb.AudioWavBase64,
            ConversationId: pb.ConversationId);
    }
}
