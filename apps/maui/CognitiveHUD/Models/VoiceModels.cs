namespace SextaFeira.CognitiveHUD.Models;

/// <summary>Status of the voice subsystem.</summary>
public record VoiceStatus(
    bool IsEnabled,
    bool SttAvailable,
    bool TtsAvailable);

/// <summary>Result of transcribing audio to text.</summary>
public record TranscriptResult(
    string Text,
    double? Confidence = null);

/// <summary>Full voice chat cycle result (transcribe → think → speak).</summary>
public record VoiceChatResult(
    string Transcript,
    string Reply,
    string? AudioWavBase64 = null,
    string? ConversationId = null);

/// <summary>Voice recording state.</summary>
public enum VoiceRecordingState
{
    Idle,
    RequestingPermission,
    Recording,
    Processing,
    Error,
}
