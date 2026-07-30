using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Models;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class EventBusViewModel : ObservableObject
{
    private readonly IEventBus _eventBus;

    public EventBusViewModel(IEventBus eventBus)
    {
        _eventBus = eventBus;

        // Subscribe to all events for the log
        _eventBus.Subscribe("*", evt =>
        {
            EventLog.Insert(0, evt);

            // Keep only last 100 events
            while (EventLog.Count > 100)
                EventLog.RemoveAt(EventLog.Count - 1);

            TotalEvents = EventLog.Count;
            return Task.CompletedTask;
        });
    }

    [ObservableProperty] private ObservableCollection<SystemEvent> _eventLog = new();
    [ObservableProperty] private int _totalEvents;
    [ObservableProperty] private string? _filterType;

    public IReadOnlyList<SystemEvent> FilteredEvents
    {
        get
        {
            if (string.IsNullOrWhiteSpace(FilterType))
                return EventLog.ToList().AsReadOnly();
            return EventLog.Where(e => e.EventType.Contains(FilterType)).ToList().AsReadOnly();
        }
    }
}
