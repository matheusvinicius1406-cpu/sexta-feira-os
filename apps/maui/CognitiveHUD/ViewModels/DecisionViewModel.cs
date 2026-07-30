using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class DecisionViewModel : ObservableObject
{
    private readonly IEventBus _eventBus;

    public DecisionViewModel(IEventBus eventBus)
    {
        _eventBus = eventBus;
        RecentDecisions.Add(new("buscar_dados", "executing", "Buscar dados externos", DateTime.UtcNow.AddSeconds(-5)));
        RecentDecisions.Add(new("responder_usuario", "queued", "Responder ao usuário", DateTime.UtcNow.AddSeconds(-12)));
        RecentDecisions.Add(new("analisar_contexto", "completed", "Analisar contexto da conversa", DateTime.UtcNow.AddSeconds(-30)));
    }

    [ObservableProperty]
    private ObservableCollection<DecisionEntry> _recentDecisions = new();

    [ObservableProperty] private int _totalDecisions = 142;
    [ObservableProperty] private double _avgExecutionMs = 45.3;
    [ObservableProperty] private bool _isLoading;
}

public record DecisionEntry(string Id, string Status, string Description, DateTime Timestamp);
