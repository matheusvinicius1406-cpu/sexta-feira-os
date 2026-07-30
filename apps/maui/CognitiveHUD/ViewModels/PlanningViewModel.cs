using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class PlanningViewModel : ObservableObject
{
    private readonly IEventBus _eventBus;

    public PlanningViewModel(IEventBus eventBus)
    {
        _eventBus = eventBus;
        ActivePlans.Add(new("Otimizar buscas", 0.6, 3, 5));
        ActivePlans.Add(new("Aprender preferências", 0.3, 1, 4));
        ActivePlans.Add(new("Melhorar respostas", 0.8, 4, 5));
    }

    [ObservableProperty]
    private ObservableCollection<PlanEntry> _activePlans = new();

    [ObservableProperty] private int _activeCount = 3;
    [ObservableProperty] private int _completedCount = 12;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;
}

public record PlanEntry(string Name, double Progress, int StepsDone, int StepsTotal);
