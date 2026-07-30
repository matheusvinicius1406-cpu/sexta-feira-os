using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>ViewModel for system metrics — CPU, memory, latency, tokens.</summary>
public partial class MetricsViewModel : ObservableObject
{
    [ObservableProperty] private string _cpuUsage = "—%";
    [ObservableProperty] private string _memoryUsage = "— MB";
    [ObservableProperty] private string _latency = "— ms";
    [ObservableProperty] private string _tokensUsed = "—";
    [ObservableProperty] private string _queueDepth = "—";
    [ObservableProperty] private bool _isLoading;

    [RelayCommand]
    private async Task RefreshAsync()
    {
        IsLoading = true;
        await Task.Delay(100); // placeholder for real metrics
        IsLoading = false;
    }
}
