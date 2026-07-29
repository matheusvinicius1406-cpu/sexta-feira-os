namespace SextaFeira.UIEngine.Navigation;

/// <summary>
/// A node in the radial navigation tree. Each node represents a
/// module, sub-module, or action in the HUD.
///
/// The tree structure enables layer-based navigation:
/// Core > Memória > Conhecimento > RAG
/// Each level replaces the previous with a radial transition.
/// </summary>
public class NavigationNode
{
    // ── Identity ──────────────────────────────────────────
    public string Id { get; }
    public string Label { get; }
    public string Icon { get; }
    public string ModuleColor { get; }
    public bool IsLeaf { get; private set; }

    // ── Tree ──────────────────────────────────────────────
    public NavigationNode? Parent { get; private set; }
    private readonly List<NavigationNode> _children = new();
    public IReadOnlyList<NavigationNode> Children => _children.AsReadOnly();

    // ── Metadata ──────────────────────────────────────────
    public string? Description { get; set; }
    public object? Tag { get; set; }
    public string? Route { get; set; } // API route or action

    /// <summary>
    /// Action to execute when this node is activated.
    /// For leaf nodes: opens a specific function (chat, memories, etc.)
    /// For branch nodes: opens the next layer of navigation.
    /// </summary>
    public Func<Task>? OnActivate { get; set; }

    public NavigationNode(string id, string label, string icon, string moduleColor, bool isLeaf = false)
    {
        Id = id;
        Label = label;
        Icon = icon;
        ModuleColor = moduleColor;
        IsLeaf = isLeaf;
    }

    // ── Tree management ───────────────────────────────────
    public NavigationNode AddChild(NavigationNode child)
    {
        child.Parent = this;
        _children.Add(child);
        return this;
    }

    public NavigationNode AddChildren(params NavigationNode[] children)
    {
        foreach (var child in children)
        {
            child.Parent = this;
            _children.Add(child);
        }
        return this;
    }

    public NavigationNode? FindChild(string id)
    {
        if (Id == id) return this;

        foreach (var child in _children)
        {
            var found = child.FindChild(id);
            if (found != null) return found;
        }
        return null;
    }

    // ── Depth level (0 = root) ────────────────────────────
    public int Depth
    {
        get
        {
            int depth = 0;
            var current = Parent;
            while (current != null)
            {
                depth++;
                current = current.Parent;
            }
            return depth;
        }
    }

    // ── Factory helpers ───────────────────────────────────
    public static NavigationNode Leaf(string id, string label, string icon, string color)
        => new(id, label, icon, color, isLeaf: true);

    public static NavigationNode Branch(string id, string label, string icon, string color)
        => new(id, label, icon, color, isLeaf: false);
}
