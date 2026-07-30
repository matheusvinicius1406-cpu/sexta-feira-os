using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>ViewModel for developer tools — API explorer, plugin dev, debug console.</summary>
public partial class DeveloperViewModel : ObservableObject
{
    [ObservableProperty]
    private ObservableCollection<string> _tools = new();

    [ObservableProperty] private string _selectedTool = "";
    [ObservableProperty] private string _consoleOutput = "";
    [ObservableProperty] private bool _isLoading;

    public DeveloperViewModel()
    {
        Tools = new ObservableCollection<string>
        {
            "Explorar APIs", "Testar Plugins", "Console", "Event Viewer"
        };
    }

    [RelayCommand]
    private void SelectTool(string tool)
    {
        SelectedTool = tool;
        ConsoleOutput = $"> modo {tool} ativado\n";
    }

    [RelayCommand]
    private async Task ExecuteCommandAsync(string command)
    {
        IsLoading = true;
        await Task.Delay(50);
        ConsoleOutput += $"> {command}\n  → executado\n";
        IsLoading = false;
    }
}
