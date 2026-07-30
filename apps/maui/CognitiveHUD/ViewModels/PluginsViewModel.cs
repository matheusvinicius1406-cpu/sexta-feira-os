using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class PluginsViewModel : ObservableObject
{
    private readonly PluginService _pluginService;

    public PluginsViewModel(PluginService pluginService)
    {
        _pluginService = pluginService;
    }

    [ObservableProperty] private ObservableCollection<PluginManifest> _plugins = new();
    [ObservableProperty] private int _pluginCount;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;

    [RelayCommand]
    private void RefreshPlugins()
    {
        IsLoading = true;
        try
        {
            var count = _pluginService.LoadAll();
            PluginCount = _pluginService.Count;
            Plugins.Clear();
            foreach (var manifest in _pluginService.ListCapabilities())
                Plugins.Add(manifest);
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
