using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Models;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>
/// ViewModel for voice operations — recording, transcription, TTS, voice chat.
/// Mirrors Python VoiceAdapter in the C# layer.
/// </summary>
public partial class VoiceViewModel : ObservableObject
{
    private readonly IVoiceService _voiceService;
    private readonly IEventBus _eventBus;

    public VoiceViewModel(IVoiceService voiceService, IEventBus eventBus)
    {
        _voiceService = voiceService;
        _eventBus = eventBus;
    }

    // ── Observable State ─────────────────────────────────

    [ObservableProperty]
    private VoiceStatus _status = new(false, false, false);

    [ObservableProperty]
    private VoiceRecordingState _recordingState = VoiceRecordingState.Idle;

    [ObservableProperty]
    private string _transcribedText = "";

    [ObservableProperty]
    private string? _lastReply;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _errorMessage;

    // ── Commands ─────────────────────────────────────────

    [RelayCommand]
    private async Task LoadStatusAsync()
    {
        IsLoading = true;
        try
        {
            Status = await _voiceService.GetStatusAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao carregar status de voz: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private void StartRecording()
    {
        RecordingState = VoiceRecordingState.Recording;
        TranscribedText = "";
        LastReply = null;
        ErrorMessage = null;
    }

    [RelayCommand]
    private void StopRecording()
    {
        if (RecordingState == VoiceRecordingState.Recording)
            RecordingState = VoiceRecordingState.Processing;
    }

    public async Task OnAudioCapturedAsync(byte[] audioBytes)
    {
        if (audioBytes.Length == 0)
        {
            RecordingState = VoiceRecordingState.Idle;
            return;
        }

        RecordingState = VoiceRecordingState.Processing;
        IsLoading = true;
        ErrorMessage = null;

        try
        {
            var result = await _voiceService.VoiceChatAsync(audioBytes, speakReply: true);
            if (result is not null)
            {
                TranscribedText = result.Transcript;
                LastReply = result.Reply;
            }
            RecordingState = VoiceRecordingState.Idle;
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro no áudio: {ex.Message}";
            RecordingState = VoiceRecordingState.Error;
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private void ResetState()
    {
        RecordingState = VoiceRecordingState.Idle;
        TranscribedText = "";
        LastReply = null;
        ErrorMessage = null;
    }
}
