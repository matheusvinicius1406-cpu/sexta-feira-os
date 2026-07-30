using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class LearningViewModel : ObservableObject
{
    private readonly IEventBus _eventBus;

    public LearningViewModel(IEventBus eventBus)
    {
        _eventBus = eventBus;
        LearnedPatterns.Add(new("Saudação matinal", 0.92, 23));
        LearnedPatterns.Add(new("Preferência musical", 0.78, 15));
        LearnedPatterns.Add(new("Horário de trabalho", 0.85, 31));
    }

    [ObservableProperty]
    private ObservableCollection<LearnedPattern> _learnedPatterns = new();

    [ObservableProperty] private int _activeSkills = 3;
    [ObservableProperty] private double _avgConfidence = 0.85;
    [ObservableProperty] private int _totalSamples = 69;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;
}

public record LearnedPattern(string Name, double Confidence, int SampleCount);
