namespace SextaFeira.CognitiveHUD.Models;

/// <summary>Memory node DTO — mirrors Python MemoryItem dataclass.</summary>
public record MemoryNode(
    string Id,
    string Content,
    string Title,
    string Kind,
    double Importance,
    string Source,
    DateTime? CreatedAt = null,
    DateTime? UpdatedAt = null);

/// <summary>Memory link (edge between two nodes).</summary>
public record MemoryLink(
    string Id,
    string SourceId,
    string TargetId,
    string Label);

/// <summary>Memory graph — nodes + edges for visualization.</summary>
public record MemoryGraph(
    IReadOnlyList<MemoryNode> Nodes,
    IReadOnlyList<MemoryLink> Links);

/// <summary>Search result with query metadata.</summary>
public record MemorySearchResult(
    IReadOnlyList<MemoryNode> Results,
    int Total,
    string Query);

/// <summary>Memory kind enum — mirrors Python kind mapping.</summary>
public static class MemoryKind
{
    public const int Unspecified = 0;
    public const int Fact = 1;
    public const int Preference = 2;
    public const int Concept = 3;
    public const int Person = 4;
    public const int Project = 5;
    public const int Note = 6;
    public const int Conversation = 7;
}

/// <summary>Relation type enum — mirrors Python relation mapping.</summary>
public static class RelationType
{
    public const int Related = 0;
    public const int CreatedBy = 1;
    public const int Mentions = 2;
    public const int Causes = 3;
    public const int DependsOn = 4;
    public const int Opposes = 5;
}
