using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Event Bus contract — mirrors Python's EventBus interface.
/// Enables decoupled communication between Engines and UI.
/// </summary>
public interface IEventBus
{
    /// <summary>Publish an event to all subscribers.</summary>
    Task PublishAsync(string eventType, Dictionary<string, object>? data = null);

    /// <summary>Subscribe to an event type. Returns a listener ID for unsubscription.</summary>
    string Subscribe(string eventType, Func<SystemEvent, Task> handler);

    /// <summary>Unsubscribe a listener by ID.</summary>
    void Unsubscribe(string listenerId);
}
