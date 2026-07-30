using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class SchedulerViewModel : ObservableObject
{
    private readonly IEventBus _eventBus;

    public SchedulerViewModel(IEventBus eventBus)
    {
        _eventBus = eventBus;
        UpcomingReminders.Add(new("Revisar tarefas", DateTime.UtcNow.AddHours(1), "pending"));
        UpcomingReminders.Add(new("Backup semanal", DateTime.UtcNow.AddHours(3), "scheduled"));
        UpcomingReminders.Add(new("Sincronizar memória", DateTime.UtcNow.AddMinutes(30), "pending"));
    }

    [ObservableProperty]
    private ObservableCollection<ReminderItem> _upcomingReminders = new();

    [ObservableProperty] private int _totalReminders = 3;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;
}

public record ReminderItem(string Title, DateTime DueAt, string Status);
