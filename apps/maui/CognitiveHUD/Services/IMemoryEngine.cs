using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Memory Engine contract — mirrors Python MemoryEngine.
/// Manages memory CRUD, graph, and semantic search.
/// </summary>
public interface IMemoryEngine : IEngine
{
    Task<MemoryNode?> CreateMemoryAsync(string content, string? title = null, int kind = 0);
    Task<MemoryNode?> GetMemoryAsync(string memoryId);
    Task<bool> DeleteMemoryAsync(string memoryId);
    Task<MemorySearchResult> SearchMemoryAsync(string query, int limit = 10);
    Task<MemoryLink?> LinkMemoriesAsync(string sourceId, string targetId, string relation = "related");
    Task<bool> UnlinkMemoriesAsync(string linkId);
    Task<IReadOnlyList<MemoryLink>> GetNeighboursAsync(string memoryId);
    Task<MemoryGraph?> GetMemoryGraphAsync(int maxNodes = 50);
}
