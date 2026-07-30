using SextaFeira.CognitiveHUD.Models;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// Memory service — mirrors Python MemoryAdapter.
/// Wraps gRPC memory operations with domain-appropriate DTOs.
/// </summary>
public class MemoryService : IMemoryService
{
    private readonly GrpcClient _grpc;
    private readonly IEventBus _eventBus;

    public MemoryService(GrpcClient grpc, IEventBus eventBus)
    {
        _grpc = grpc;
        _eventBus = eventBus;
    }

    public async Task<MemoryNode?> CreateMemoryAsync(string content, string? title = null, int kind = 0)
    {
        var pb = await _grpc.CreateMemoryAsync(content, title, kind);
        if (pb is null) return null;

        var node = ToMemoryNode(pb);

        await _eventBus.PublishAsync("memory.created", new Dictionary<string, object>
        {
            ["id"] = node.Id,
            ["content"] = node.Content.Length > 200 ? node.Content[..200] : node.Content,
        });

        return node;
    }

    public async Task<MemoryNode?> GetMemoryAsync(string memoryId)
    {
        var pb = await _grpc.GetMemoryCoreAsync(memoryId);
        return pb is not null ? ToMemoryNode(pb) : null;
    }

    public async Task<bool> DeleteMemoryAsync(string memoryId)
    {
        var success = await _grpc.DeleteMemoryCoreAsync(memoryId);
        if (success)
            await _eventBus.PublishAsync("memory.deleted", new Dictionary<string, object> { ["id"] = memoryId });
        return success;
    }

    public async Task<MemorySearchResult> SearchMemoryAsync(string query, int limit = 10)
    {
        var results = await _grpc.SearchMemoryAsync(query, limit);
        var nodes = results.Select(ToMemoryNode).ToList();

        await _eventBus.PublishAsync("memory.searched", new Dictionary<string, object>
        {
            ["query"] = query.Length > 100 ? query[..100] : query,
            ["count"] = nodes.Count,
        });

        return new MemorySearchResult(nodes.AsReadOnly(), nodes.Count, query);
    }

    public async Task<MemoryLink?> LinkMemoriesAsync(string sourceId, string targetId, string relation = "related")
    {
        var pb = await _grpc.LinkMemoriesCoreAsync(sourceId, targetId, relation);
        if (pb is null) return null;

        var link = new MemoryLink(pb.Id, pb.SourceId, pb.TargetId, pb.Label);

        await _eventBus.PublishAsync("memory.linked", new Dictionary<string, object>
        {
            ["source_id"] = link.SourceId, ["target_id"] = link.TargetId, ["relation"] = link.Label,
        });

        return link;
    }

    public async Task<bool> UnlinkMemoriesAsync(string linkId)
    {
        var success = await _grpc.UnlinkMemoriesCoreAsync(linkId);
        if (success)
            await _eventBus.PublishAsync("memory.unlinked", new Dictionary<string, object> { ["link_id"] = linkId });
        return success;
    }

    public async Task<IReadOnlyList<MemoryLink>> GetNeighboursAsync(string memoryId)
    {
        var pb = await _grpc.GetNeighboursCoreAsync(memoryId);
        if (pb is null) return Array.Empty<MemoryLink>();

        return pb.Links.Select(l => new MemoryLink(l.Id, l.SourceId, l.TargetId, l.Label)).ToList().AsReadOnly();
    }

    public async Task<MemoryGraph?> GetMemoryGraphAsync(int maxNodes = 50)
    {
        var pb = await _grpc.GetMemoryGraphAsync(maxNodes);
        if (pb is null) return null;

        var nodes = pb.Nodes.Select(n => new MemoryNode(
            Id: n.Id, Content: "", Title: n.Label,
            Kind: n.Kind.ToString(), Importance: n.Importance,
            Source: "")).ToList();

        var edges = pb.Links.Select(e => new MemoryLink(
            Id: "", SourceId: e.SourceId, TargetId: e.TargetId, Label: e.Label)).ToList();

        return new MemoryGraph(nodes.AsReadOnly(), edges.AsReadOnly());
    }

    private static MemoryNode ToMemoryNode(CognitiveCore.V1.MemoryNode pb)
    {
        return new MemoryNode(
            Id: pb.Id, Content: pb.Content, Title: pb.Title ?? "",
            Kind: pb.Kind.ToString(), Importance: pb.Importance,
            Source: pb.Source,
            CreatedAt: pb.CreatedAt?.ToDateTime(),
            UpdatedAt: pb.UpdatedAt?.ToDateTime());
    }
}
