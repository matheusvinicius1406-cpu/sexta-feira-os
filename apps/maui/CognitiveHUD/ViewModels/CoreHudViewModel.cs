using System.Collections.ObjectModel;
using System.Linq;
using CommunityToolkit.Mvvm.ComponentModel;
using SextaFeira.CognitiveHUD.Services;
using SextaFeira.UIEngine.Base;
using SextaFeira.UIEngine.Controls;
using SextaFeira.UIEngine.Themes;
// NavigationEventArgs from our UI Engine (not Microsoft.Maui.Controls)
using NavEventArgs = SextaFeira.UIEngine.Navigation.NavigationEventArgs;
using NavigationController = SextaFeira.UIEngine.Navigation.NavigationController;
using NavigationNode = SextaFeira.UIEngine.Navigation.NavigationNode;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>
/// Main ViewModel for the Sexta-Feira Cognitive HUD.
/// Orchestrates the full layer-transition experience:
/// collapse → particle burst → swap items → expand → update depth.
/// </summary>
public partial class CoreHudViewModel : ObservableObject
{
    /// <summary>Default radius of the core circle, exposed for drawable calculations.</summary>
    public const float CoreRadiusDefault = 60f;

    private readonly ApiClient _apiClient;
    private readonly NavigationController _navigationController;
    private readonly ThemeController _themeController;

    // ── Exposed theme ─────────────────────────────────────
    public ITheme CurrentTheme => _themeController.CurrentTheme;

    // ── Core Circle ────────────────────────────────────────
    [ObservableProperty]
    private CoreCircle _coreCircle = new();

    [ObservableProperty]
    private string _statusText = "Sexta-Feira";

    [ObservableProperty]
    private string _subtitleText = "toque para ativar";

    [ObservableProperty]
    private bool _isCoreExpanded;

    // ── Radial Menu ────────────────────────────────────────
    [ObservableProperty]
    private RadialMenu? _radialMenu;

    [ObservableProperty]
    private bool _isMenuVisible;

    // ── Navigation ─────────────────────────────────────────
    [ObservableProperty]
    private string _breadcrumbText = "Core";

    [ObservableProperty]
    private bool _canGoBack;

    [ObservableProperty]
    private int _currentDepth;

    // ── Connection ─────────────────────────────────────────
    [ObservableProperty]
    private bool _isConnected;

    [ObservableProperty]
    private string _connectionStatus = "Desconectado";

    // ── Ambient orbital particles ─────────────────────────
    public ObservableCollection<OrbitalItem> AmbientOrbitals { get; } = new();

    // ── Transition particle burst ─────────────────────────
    public ParticleBurst TransitionBurst { get; } = new();

    public CoreHudViewModel(
        ApiClient apiClient,
        NavigationController navigationController,
        ThemeController themeController)
    {
        _apiClient = apiClient;
        _navigationController = navigationController;
        _themeController = themeController;

        InitializeAmbientOrbitals();
        InitializeMenuItems();

        _navigationController.OnNavigationChanged += OnNavigationChanged;
        _themeController.OnThemeChanged += OnThemeChanged;

        _ = CheckConnectionAsync();
    }

    // ── Initialize ambient orbitals ──────────────────────
    private void InitializeAmbientOrbitals()
    {
        var theme = _themeController.CurrentTheme;

        for (int i = 0; i < 5; i++)
        {
            AmbientOrbitals.Add(new OrbitalItem(i * 72f)
            {
                OrbitRadius = 80f + i * 15f,
                OrbitSpeed = 0.15f + i * 0.05f,
                Radius = 2f + i * 0.5f,
                Color = theme.ColorForModule(i % 2 == 0 ? "ia" : "memory"),
                Opacity = 0.3f - i * 0.04f,
                Clockwise = i % 2 == 0,
            });
        }
    }

    // ── Initialize radial menu ───────────────────────────
    private void InitializeMenuItems()
    {
        var theme = _themeController.CurrentTheme;
        var items = BuildMenuItemsFromNodes(_navigationController.CurrentLevel, theme);
        RadialMenu = new RadialMenu(0, 0);
        RadialMenu.AddItems(items);

        // Wire up transition midpoint for depth changes
        RadialMenu.OnTransitionMidpoint += () =>
        {
            // Fire particle burst at midpoint
            float cx = (float)(RadialMenu?.CenterX ?? 0f);
            float cy = (float)(RadialMenu?.CenterY ?? 0f);
            // Read through the generated property, not the backing field —
            // the field bypasses change notification.
            TransitionBurst.ParticleCount = 30 + CurrentDepth * 10;
            TransitionBurst.Play(cx, cy);

            // Update core status for the new depth
            CoreCircle.StatusText = _navigationController.CurrentDepth == 0
                ? "Sexta-Feira"
                : _navigationController.CurrentNode?.Label ?? "Sexta-Feira";
        };
    }

    private static List<RadialMenuItem> BuildMenuItemsFromNodes(
        IReadOnlyList<NavigationNode> nodes, ITheme theme)
    {
        return nodes.Select(node => new RadialMenuItem(
            node.Id,
            node.Label,
            node.Icon,
            theme.ColorForModule(node.ModuleColor),
            0, 0)).ToList();
    }

    /// <summary>
    /// Rebuilds the menu items from the current navigation level
    /// and triggers a smooth TransitionTo animation.
    /// </summary>
    private void TransitionToCurrentLevel()
    {
        if (RadialMenu == null) return;

        var theme = _themeController.CurrentTheme;
        var items = BuildMenuItemsFromNodes(_navigationController.CurrentLevel, theme);
        RadialMenu.TransitionTo(items);
    }

    // ── Navigation handlers ──────────────────────────────
    private void OnNavigationChanged(NavEventArgs args)
    {
        var trail = _navigationController.GetBreadcrumb();
        BreadcrumbText = string.Join(" > ", trail.Select(n => n.Label));
        CanGoBack = _navigationController.CanGoBack;
        CurrentDepth = args.CurrentDepth;

        // Animate the transition to the new level
        TransitionToCurrentLevel();

        // Adapt core circle for depth
        AdaptCoreToDepth(args.CurrentDepth);
    }

    private void AdaptCoreToDepth(int depth)
    {
        if (depth == 0)
        {
            // Back to root: normal pulse
            CoreCircle.PulseSpeed = 1.5f;
            CoreCircle.GlowIntensity = 0.6f;
            CoreCircle.Radius = CoreRadiusDefault;
        }
        else
        {
            // Deeper: stronger glow, slightly larger, faster pulse
            float depthFactor = 1f + depth * 0.15f;
            CoreCircle.PulseSpeed = 1.5f + depth * 0.3f;
            CoreCircle.GlowIntensity = Math.Min(0.6f + depth * 0.1f, 0.95f);
            CoreCircle.Radius = CoreRadiusDefault * (1f + depth * 0.03f);
        }
    }

    private void OnThemeChanged(ITheme theme)
    {
        CoreCircle.Color = theme.Primary;
        CoreCircle.GlowColor = theme.GlowColor;
        CoreCircle.Radius = CoreRadiusDefault;

        if (RadialMenu != null)
        {
            RadialMenu.OrbitRadius = theme.MenuOrbitRadius;
            RadialMenu.ItemRadius = theme.MenuItemRadius;
            RadialMenu.RecalculatePositions();
        }
    }

    // ── Core interaction ──────────────────────────────────
    public void ToggleCoreExpand()
    {
        if (IsCoreExpanded) Collapse();
        else Expand();
    }

    public void Expand()
    {
        IsCoreExpanded = true;
        IsMenuVisible = true;
        SubtitleText = "selecione um módulo";
        RadialMenu?.Expand();
        CoreCircle.State = HudNodeState.Active;
        CoreCircle.TriggerRipple();
        CoreCircle.StatusText = "Sexta-Feira";

        // Small ambient burst on open
        // (actual coordinates set by drawable at render time)
    }

    public void Collapse()
    {
        IsCoreExpanded = false;
        IsMenuVisible = false;
        SubtitleText = "toque para ativar";
        RadialMenu?.Collapse();
        CoreCircle.State = HudNodeState.Idle;
    }

    // ── Module selection (layer navigation) ──────────────
    public async Task SelectModule(string moduleId)
    {
        int currentDepth = _navigationController.CurrentDepth;

        if (currentDepth == 0)
        {
            // Level 1 → Level 2: navigate into branch
            var node = _navigationController.CurrentLevel
                .FirstOrDefault(n => n.Id == moduleId);

            if (node == null) return;

            CoreCircle.StatusText = node.Label;

            if (node.IsLeaf)
            {
                // Leaf at root level — activate
                await _navigationController.ActivateNode(moduleId);
            }
            else
            {
                // Branch — navigate deeper with transition
                _navigationController.NavigateTo(moduleId);
                // TransitionToCurrentLevel is called by OnNavigationChanged
            }
        }
        else
        {
            // Level 2+ → Level 3: delegate to navigation controller
            await _navigationController.ActivateNode(moduleId);
        }
    }

    public void GoBack()
    {
        if (_navigationController.CanGoBack)
        {
            _navigationController.GoBack();
            // TransitionToCurrentLevel is called by OnNavigationChanged
        }
        else
        {
            Collapse();
        }
    }

    public void GoToRoot()
    {
        if (_navigationController.CurrentDepth > 0)
        {
            _navigationController.GoToRoot();
            // TransitionToCurrentLevel will be called by OnNavigationChanged
        }
    }

    // ── Connection ────────────────────────────────────────
    public async Task CheckConnectionAsync()
    {
        ConnectionStatus = "Conectando...";
        IsConnected = await _apiClient.CheckHealthAsync();
        ConnectionStatus = IsConnected ? "Conectado" : "Offline";
        StatusDotColor = IsConnected ? "#00E676" : "#666666";
    }

    [ObservableProperty]
    private string _statusDotColor = "#666666";

    // ── Frame update ──────────────────────────────────────
    public void Update(float deltaSeconds)
    {
        CoreCircle.UpdatePulse(deltaSeconds);
        CoreCircle.UpdateRipple(deltaSeconds);
        RadialMenu?.Update(deltaSeconds);

        foreach (var orbital in AmbientOrbitals)
        {
            orbital.Update(deltaSeconds);
        }

        TransitionBurst.Update(deltaSeconds);

        if (RadialMenu != null && RadialMenu.State == RadialMenuState.Idle)
        {
            IsMenuVisible = IsCoreExpanded;
        }
    }
}
