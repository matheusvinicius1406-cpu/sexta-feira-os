using System.Linq;
using SextaFeira.UIEngine.Animation;

namespace SextaFeira.UIEngine.Navigation;

/// <summary>
/// Navigation state change event.
/// </summary>
public record NavigationEventArgs(
    NavigationNode PreviousNode,
    NavigationNode? CurrentNode,
    int CurrentDepth,
    bool IsBackNavigation);

/// <summary>
/// Tree-based navigation controller for the radial HUD.
///
/// Features:
/// - Hierarchical tree of NavigationNodes (Core > Memória > Conhecimento)
/// - Layer-based navigation (each level replaces the previous)
/// - Full history stack (back navigation with animated reverse)
/// - Events for UI synchronization
/// - Thread-safe state management
/// </summary>
public class NavigationController
{
    // ── Tree ──────────────────────────────────────────────
    private readonly NavigationNode _root;

    // ── State ─────────────────────────────────────────────
    private NavigationNode? _currentNode;
    private readonly Stack<NavigationNode> _history = new();
    private readonly List<NavigationNode> _currentLevel = new();

    public IReadOnlyList<NavigationNode> CurrentLevel => _currentLevel.AsReadOnly();
    public NavigationNode? CurrentNode => _currentNode;
    public NavigationNode Root => _root;
    public int CurrentDepth => _currentNode?.Depth ?? 0;
    public bool CanGoBack => _history.Count > 0;
    public IReadOnlyList<NavigationNode> History => _history.Reverse().ToList().AsReadOnly();

    // ── Events ────────────────────────────────────────────
    public event Action<NavigationEventArgs>? OnNavigationChanged;
    public event Action? OnBackNavigation;
    public event Action<string>? OnNodeActivated; // Module ID

    // ── Transition control ────────────────────────────────
    public TransitionType ForwardTransition { get; set; } = TransitionType.ExpandRadial;
    public TransitionType BackTransition { get; set; } = TransitionType.CollapseRadial;

    public NavigationController(NavigationNode root)
    {
        _root = root ?? throw new ArgumentNullException(nameof(root));
        _currentNode = root;
        _currentLevel.AddRange(root.Children);
    }

    // ── Navigation ────────────────────────────────────────
    /// <summary>
    /// Navigate to a specific node by ID. Searches the tree recursively.
    /// </summary>
    public bool NavigateTo(string nodeId)
    {
        var node = _root.FindChild(nodeId);
        if (node == null || node == _currentNode) return false;

        // If on same level, just switch
        if (node.Depth == (_currentNode?.Depth ?? 0) && node.Parent == _currentNode?.Parent)
        {
            _currentNode = node;
            return true;
        }

        // Push current node to history before going deeper
        if (_currentNode != null)
        {
            _history.Push(_currentNode);
        }

        var previous = _currentNode;
        _currentNode = node;
        _currentLevel.Clear();
        _currentLevel.AddRange(node.Children);

        var args = new NavigationEventArgs(
            previous ?? _root,
            _currentNode,
            CurrentDepth,
            IsBackNavigation: false);

        OnNavigationChanged?.Invoke(args);
        return true;
    }

    /// <summary>
    /// Go back one level in the navigation tree.
    /// </summary>
    public bool GoBack()
    {
        if (!CanGoBack) return false;

        var previous = _currentNode;
        _currentNode = _history.Pop();

        _currentLevel.Clear();
        _currentLevel.AddRange(_currentNode?.Children ?? _root.Children);

        var args = new NavigationEventArgs(
            previous ?? _root,
            _currentNode,
            CurrentDepth,
            IsBackNavigation: true);

        OnNavigationChanged?.Invoke(args);
        OnBackNavigation?.Invoke();
        return true;
    }

    /// <summary>
    /// Go back to root (Core) level.
    /// </summary>
    public void GoToRoot()
    {
        _history.Clear();
        var previous = _currentNode;
        _currentNode = _root;
        _currentLevel.Clear();
        _currentLevel.AddRange(_root.Children);

        var args = new NavigationEventArgs(
            previous ?? _root,
            _currentNode,
            0,
            IsBackNavigation: true);

        OnNavigationChanged?.Invoke(args);
    }

    /// <summary>
    /// Activate a node at the current level by ID.
    /// If the node is a branch, navigates into it.
    /// If the node is a leaf, fires the activation event.
    /// </summary>
    public async Task ActivateNode(string nodeId)
    {
        var node = _currentLevel.FirstOrDefault(n => n.Id == nodeId);
        if (node == null) return;

        if (node.IsLeaf)
        {
            // Leaf node — activate action
            OnNodeActivated?.Invoke(nodeId);
            if (node.OnActivate != null)
            {
                await node.OnActivate();
            }
        }
        else
        {
            // Branch node — navigate into it
            NavigateTo(nodeId);
        }
    }

    /// <summary>
    /// Gets the breadcrumb trail from root to current node.
    /// </summary>
    public List<NavigationNode> GetBreadcrumb()
    {
        var trail = new List<NavigationNode>();
        var current = _currentNode;

        while (current != null)
        {
            trail.Insert(0, current);
            current = current.Parent;
        }

        return trail;
    }

    /// <summary>
    /// Resets navigation to root state.
    /// </summary>
    public void Reset()
    {
        _history.Clear();
        _currentNode = _root;
        _currentLevel.Clear();
        _currentLevel.AddRange(_root.Children);
    }
}
