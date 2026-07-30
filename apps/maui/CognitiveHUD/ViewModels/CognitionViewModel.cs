using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Models;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>
/// ViewModel for cognition/chat — message list, streaming, thinking state.
/// Mirrors Python CognitionAdapter in the C# layer.
/// </summary>
public partial class CognitionViewModel : ObservableObject
{
    private readonly ICognitionService _cognitionService;
    private readonly IEventBus _eventBus;

    public CognitionViewModel(ICognitionService cognitionService, IEventBus eventBus)
    {
        _cognitionService = cognitionService;
        _eventBus = eventBus;
    }

    // ── Observable State ─────────────────────────────────

    [ObservableProperty]
    private ObservableCollection<ChatMessage> _messages = new();

    [ObservableProperty]
    private string _messageInput = "";

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isThinking;

    [ObservableProperty]
    private string? _errorMessage;

    [ObservableProperty]
    private bool _isConnected;

    [ObservableProperty]
    private string _connectionStatus = "Desconectado";

    private string? _currentConversationId;

    // ── Commands ─────────────────────────────────────────

    [RelayCommand]
    private async Task CheckHealthAsync()
    {
        try
        {
            var health = await _cognitionService.CheckHealthAsync();
            IsConnected = health.IsOnline;
            ConnectionStatus = IsConnected ? "Conectado" : "Offline";
        }
        catch
        {
            IsConnected = false;
            ConnectionStatus = "Erro de conexão";
        }
    }

    [RelayCommand]
    private async Task SendMessageAsync()
    {
        var text = MessageInput?.Trim();
        if (string.IsNullOrEmpty(text)) return;

        MessageInput = "";

        var userMsg = new ChatMessage(
            Id: Guid.NewGuid().ToString(),
            Role: "user",
            Content: text,
            Timestamp: DateTime.UtcNow);

        Messages.Add(userMsg);
        IsLoading = true;
        IsThinking = true;
        ErrorMessage = null;

        var assistantId = Guid.NewGuid().ToString();
        var assistantMsg = new ChatMessage(
            Id: assistantId,
            Role: "assistant",
            Content: "",
            Timestamp: DateTime.UtcNow,
            IsStreaming: true);

        Messages.Add(assistantMsg);

        try
        {
            var replyBuilder = new System.Text.StringBuilder();
            // Store the index once — assistantMsg is always the last message
            int msgIndex = Messages.Count - 1;

            await foreach (var token in _cognitionService.ChatStreamAsync(text, _currentConversationId))
            {
                replyBuilder.Append(token);

                // Update the streaming message by index (records use value equality, so IndexOf fails)
                Messages[msgIndex] = Messages[msgIndex] with
                {
                    Content = replyBuilder.ToString(),
                    IsStreaming = true,
                };
            }

            // Mark as done streaming
            var finalIdx = Messages.IndexOf(assistantMsg);
            if (finalIdx >= 0)
            {
                Messages[finalIdx] = Messages[finalIdx] with { IsStreaming = false };
            }
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro: {ex.Message}";
            var errIdx = Messages.IndexOf(assistantMsg);
            if (errIdx >= 0)
            {
                Messages[errIdx] = Messages[errIdx] with
                {
                    Content = $"❌ {ex.Message}",
                    IsStreaming = false,
                };
            }
        }
        finally
        {
            IsLoading = false;
            IsThinking = false;
        }
    }

    [RelayCommand]
    private void ClearMessages()
    {
        Messages.Clear();
        _currentConversationId = null;
        ErrorMessage = null;
    }
}
