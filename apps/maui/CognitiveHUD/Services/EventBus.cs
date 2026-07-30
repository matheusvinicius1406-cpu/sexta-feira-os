using System.Collections.Concurrent;
using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// In-memory Event Bus implementation using System.Threading.Channels.
/// Mirrors the Python asyncio.Queue-based EventBus.
/// </summary>
public sealed class EventBus : IEventBus, IDisposable
{
    private readonly ConcurrentDictionary<string, List<Subscriber>> _subscribers = new();
    private readonly ConcurrentDictionary<string, Subscriber> _listeners = new();
    private readonly object _lock = new();
    private bool _disposed;

    /// <summary>Publish an event to all matching subscribers.</summary>
    public Task PublishAsync(string eventType, Dictionary<string, object>? data = null)
    {
        if (_disposed) return Task.CompletedTask;

        var evt = new SystemEvent(eventType, data ?? new Dictionary<string, object>());
        List<Subscriber>? handlers;

        // Get exact-match subscribers
        if (_subscribers.TryGetValue(eventType, out handlers))
        {
            var snapshot = handlers.ToArray();
            foreach (var sub in snapshot)
            {
                _ = FireHandler(sub, evt);
            }
        }

        // Get wildcard subscribers ("*")
        if (_subscribers.TryGetValue("*", out handlers))
        {
            var snapshot = handlers.ToArray();
            foreach (var sub in snapshot)
            {
                _ = FireHandler(sub, evt);
            }
        }

        return Task.CompletedTask;
    }

    private static async Task FireHandler(Subscriber sub, SystemEvent evt)
    {
        try
        {
            await sub.Handler(evt);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[EventBus] Handler error: {ex.Message}");
        }
    }

    /// <summary>Subscribe to an event type. Returns listener ID.</summary>
    public string Subscribe(string eventType, Func<SystemEvent, Task> handler)
    {
        var subscriber = new Subscriber(Guid.NewGuid().ToString(), handler);
        _listeners[subscriber.Id] = subscriber;

        var handlers = _subscribers.GetOrAdd(eventType, _ => new List<Subscriber>());
        lock (_lock)
        {
            handlers.Add(subscriber);
        }

        return subscriber.Id;
    }

    /// <summary>Unsubscribe a listener by ID.</summary>
    public void Unsubscribe(string listenerId)
    {
        if (!_listeners.TryRemove(listenerId, out var sub)) return;

        foreach (var (_, handlers) in _subscribers)
        {
            lock (_lock)
            {
                handlers.RemoveAll(h => h.Id == listenerId);
            }
        }
    }

    public void Dispose()
    {
        _disposed = true;
        _subscribers.Clear();
        _listeners.Clear();
    }

    private sealed record Subscriber(string Id, Func<SystemEvent, Task> Handler);
}
