using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Memory service contract — mirrors Python MemoryAdapter.
/// Wraps gRPC memory operations behind an async interface.
/// </summary>
public interface IMemoryService
{
    /// <summary>Create a new memory node.</summary>
    Task<MemoryNode?> CreateMemoryAsync(string content, string? title = null, int kind = 0);

    /// <summary>Get a memory node by its ID.</summary>
    Task<MemoryNode?> GetMemoryAsync(string memoryId);

    /// <summary>Delete a memory node by its ID.</summary>
    Task<bool> DeleteMemoryAsync(string memoryId);

    /// <summary>Search memory by semantic query.</summary>
    Task<MemorySearchResult> SearchMemoryAsync(string query, int limit = 10);

    /// <summary>Link two memory nodes.</summary>
    Task<MemoryLink?> LinkMemoriesAsync(string sourceId, string targetId, string relation = "related");

    /// <summary>Unlink two memory nodes.</summary>
    Task<bool> UnlinkMemoriesAsync(string linkId);

    /// <summary>Get neighbours of a memory node.</summary>
    Task<IReadOnlyList<MemoryLink>> GetNeighboursAsync(string memoryId);

    /// <summary>Get the full memory graph.</summary>
    Task<MemoryGraph?> GetMemoryGraphAsync(int maxNodes = 50);
}
