using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Models;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class KernelViewModel : ObservableObject
{
    private readonly KernelService _kernelService;
    private readonly IEventBus _eventBus;

    public KernelViewModel(KernelService kernelService, IEventBus eventBus)
    {
        _kernelService = kernelService;
        _eventBus = eventBus;
    }

    [ObservableProperty] private bool _isAlive;
    [ObservableProperty] private HealthStatus _health = new(false, "unknown", "unknown", false, false, 0);
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;

    [RelayCommand]
    private async Task RefreshAsync()
    {
        IsLoading = true;
        ErrorMessage = null;
        try
        {
            IsAlive = await _kernelService.IsAliveAsync();
            Health = await _kernelService.GetHealthAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = ex.Message;
        }
        finally
        {
            IsLoading = false;
        }
    }
}
