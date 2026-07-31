namespace SextaFeira.UIEngine.Reactor;

/// <summary>An orbital item: an icon plus a caption.</summary>
public readonly record struct ArcItem(string Label, ArcIconKind Icon);

/// <summary>A level-1 module and the children it opens.</summary>
public sealed record ArcModule(string Id, string Label, ArcIconKind Icon, string[] Children);

/// <summary>
/// The navigation graph. Twelve modules is deliberate: 360°/12 = 30° per
/// sector, the smallest angle that still fits an icon and its caption
/// without collision at 1280px wide.
/// </summary>
public static class ArcModules
{
    public static readonly ArcModule[] All =
    {
        new("ai",       "AI",       ArcIconKind.Hex,    new[] { "Models", "Prompts", "Context", "Tuning", "Evals" }),
        new("memory",   "Memory",   ArcIconKind.Layers, new[] { "Recent", "Semantic", "Episodic", "Purge" }),
        new("agents",   "Agents",   ArcIconKind.Nodes,  new[] { "Active", "Queue", "Registry", "Logs", "Spawn" }),
        new("files",    "Files",    ArcIconKind.Folder, new[] { "Recent", "Index", "Vault", "Sync" }),
        new("projects", "Projects", ArcIconKind.Grid,   new[] { "Active", "Archive", "Tasks", "Timeline" }),
        new("terminal", "Terminal", ArcIconKind.Term,   new[] { "Shell", "History", "Jobs", "SSH" }),
        new("browser",  "Browser",  ArcIconKind.Globe,  new[] { "Tabs", "Research", "Capture", "Marks" }),
        new("security", "Security", ArcIconKind.Shield, new[] { "Keys", "Audit", "Perms", "Threats" }),
        new("voice",    "Voice",    ArcIconKind.Wave,   new[] { "Listen", "Voices", "Phrases", "Latency" }),
        new("network",  "Network",  ArcIconKind.Signal, new[] { "Nodes", "Traffic", "Devices", "VPN" }),
        new("system",   "System",   ArcIconKind.Chip,   new[] { "CPU", "Memory", "Disk", "Power", "Temp" }),
        new("settings", "Settings", ArcIconKind.Gear,   new[] { "Core", "Voice", "Theme", "About" }),
    };

    /// <summary>Items currently in orbit for the given depth and selection.</summary>
    public static ArcItem[] ItemsFor(int depth, int activeIndex)
    {
        if (depth == 2 && activeIndex >= 0 && activeIndex < All.Length)
        {
            var m = All[activeIndex];
            var kids = new ArcItem[m.Children.Length];
            for (int i = 0; i < kids.Length; i++) kids[i] = new ArcItem(m.Children[i], m.Icon);
            return kids;
        }

        var top = new ArcItem[All.Length];
        for (int i = 0; i < top.Length; i++) top[i] = new ArcItem(All[i].Label, All[i].Icon);
        return top;
    }
}
