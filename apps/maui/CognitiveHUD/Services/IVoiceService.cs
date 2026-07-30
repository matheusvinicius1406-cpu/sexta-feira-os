using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Voice service contract — mirrors Python VoiceAdapter.
/// Manages STT (speech-to-text), TTS (text-to-speech), and full voice chat.
/// </summary>
public interface IVoiceService
{
    /// <summary>Get the current voice subsystem status.</summary>
    Task<VoiceStatus> GetStatusAsync();

    /// <summary>Transcribe audio bytes to text (STT).</summary>
    Task<TranscriptResult?> TranscribeAsync(byte[] audioBytes);

    /// <summary>Synthesize text to audio (TTS). Returns WAV bytes.</summary>
    Task<byte[]?> SpeakAsync(string text);

    /// <summary>Full voice loop: transcribe → think → speak.</summary>
    Task<VoiceChatResult?> VoiceChatAsync(byte[] audioBytes, bool speakReply = true);
}
