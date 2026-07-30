using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>ViewModel for real-time system logs.</summary>
public partial class LogsViewModel : ObservableObject
{
    [ObservableProperty]
    private ObservableCollection<LogEntry> _entries = new();

    [ObservableProperty] private string _filter = "";
    [ObservableProperty] private int _totalEntries;
    [ObservableProperty] private bool _isLoading;

    [RelayCommand]
    private async Task LoadAsync()
    {
        IsLoading = true;
        await Task.Delay(100);
        Entries.Insert(0, new LogEntry("system", "kernel.ready", "Sistema iniciado"));
        TotalEntries = Entries.Count;
        IsLoading = false;
    }

    [RelayCommand]
    private void ClearLogs()
    {
        Entries.Clear();
        TotalEntries = 0;
    }
}

public record LogEntry(string Source, string Event, string Message);
