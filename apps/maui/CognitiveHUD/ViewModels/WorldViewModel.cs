using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>ViewModel for World Model — entities, relationships, temporal graph.</summary>
public partial class WorldViewModel : ObservableObject
{
    private readonly IWorldModelEngine _world;
    private readonly IEventBus _eventBus;

    public WorldViewModel(IWorldModelEngine world, IEventBus eventBus)
    {
        _world = world;
        _eventBus = eventBus;
    }

    [ObservableProperty] private int _entityCount;
    [ObservableProperty] private int _relationCount;
    [ObservableProperty] private string _stateLabel = "—";
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;

    [RelayCommand]
    private async Task LoadStateAsync()
    {
        IsLoading = true;
        try
        {
            var state = await _world.GetStateAsync();
            EntityCount = state?.EntityCount ?? 0;
            RelationCount = state?.RelationCount ?? 0;
            StateLabel = state?.Label ?? "desconhecido";
        }
        catch (Exception ex) { ErrorMessage = ex.Message; }
        finally { IsLoading = false; }
    }
}
