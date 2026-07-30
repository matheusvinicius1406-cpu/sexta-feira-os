using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Voice Engine contract — mirrors Python VoiceEngine.
/// Manages STT, TTS, and full voice chat.
/// </summary>
public interface IVoiceEngine : IEngine
{
    bool Available { get; }
    Task<VoiceStatus> GetStatusAsync();
    Task<TranscriptResult?> TranscribeAsync(byte[] audioBytes);
    Task<byte[]?> SpeakAsync(string text);
    Task<VoiceChatResult?> VoiceChatAsync(byte[] audioBytes, bool speakReply = true);
}
