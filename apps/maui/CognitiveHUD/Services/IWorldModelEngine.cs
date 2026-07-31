namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// World Model Engine contract — mirrors Python WorldEngine.
/// Manages the kernel's understanding of the user's world (state, context, history).
/// </summary>
public interface IWorldModelEngine : IEngine
{
    /// <summary>
    /// Current snapshot of the world model, or null when the engine has no
    /// backing implementation yet.
    /// </summary>
    Task<WorldState?> GetStateAsync();
}

/// <summary>A snapshot of what the world model currently holds.</summary>
public record WorldState(
    int EntityCount,
    int RelationCount,
    string Label);
