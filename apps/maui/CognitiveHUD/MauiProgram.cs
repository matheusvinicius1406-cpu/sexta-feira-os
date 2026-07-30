using Microsoft.Extensions.Logging;
using SkiaSharp.Views.Maui.Controls.Hosting;
using SextaFeira.CognitiveHUD.Pages;
using SextaFeira.CognitiveHUD.Services;
using SextaFeira.CognitiveHUD.ViewModels;
using SextaFeira.CognitiveHUD.Views;
using SextaFeira.UIEngine.Animation;
using SextaFeira.UIEngine.Navigation;
using SextaFeira.UIEngine.Themes;

namespace SextaFeira.CognitiveHUD;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .UseSkiaSharp()
            .ConfigureFonts(fonts =>
            {
                fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
                fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
            });

        // Build the navigation tree root
        var navigationRoot = BuildNavigationTree();

        // ── Infrastructure Services ──────────────────────────
        builder.Services.AddSingleton<ApiClient>();
        builder.Services.AddSingleton<GrpcClient>(_ => new GrpcClient("http://127.0.0.1:50051"));
        // Startup Pipeline — mirrors Python StartupPipeline
        builder.Services.AddSingleton<MauiStartupPipeline>();

        // Event Bus — core communication backbone
        builder.Services.AddSingleton<IEventBus, EventBus>();

        // Plugin System — registry + loader + discovery + facade
        builder.Services.AddSingleton<PluginRegistry>();
        builder.Services.AddSingleton<PluginLoader>();
        builder.Services.AddSingleton<PluginDiscovery>();
        builder.Services.AddSingleton<PluginService>();

        // ── HUD Scene (SkiaSharp orchestrator) ────────────────
        builder.Services.AddSingleton(_ =>
        {
            var theme = NeonDarkTheme.Instance;
            var hudTheme = new HudTheme(
                PrimaryGlow: new SkiaSharp.SKColor(0x00, 0xE5, 0xFF),
                SecondaryGlow: new SkiaSharp.SKColor(0x7C, 0x4D, 0xFF),
                HologramColor: new SkiaSharp.SKColor(0x00, 0xE5, 0xFF),
                Background: new SkiaSharp.SKColor(0x0A, 0x0A, 0x12),
                TextPrimary: new SkiaSharp.SKColor(0xE0, 0xE0, 0xFF),
                TextSecondary: new SkiaSharp.SKColor(0x88, 0x88, 0xAA)
            );
            return new HudScene(hudTheme);
        });

        // ── Domain Services (mirror Python Adapters) ─────────
        builder.Services.AddSingleton<IMemoryService, MemoryService>();
        builder.Services.AddSingleton<ICognitionService, CognitionService>();
        builder.Services.AddSingleton<IVoiceService, VoiceService>();
        builder.Services.AddSingleton<IAutomationService, AutomationService>();
        builder.Services.AddSingleton<IActionService, ActionService>();

        // ── Higher-Level Services ────────────────────────────
        builder.Services.AddSingleton<KernelService>();
        builder.Services.AddSingleton<HudService>();

        // ── Engine Interfaces (mirror Python Engines) ────────
        builder.Services.AddSingleton<IMemoryEngine, MemoryService>();
        builder.Services.AddSingleton<ICognitionEngine, CognitionService>();
        builder.Services.AddSingleton<IVoiceEngine, VoiceService>();
        builder.Services.AddSingleton<IAutomationEngine, AutomationService>();
        builder.Services.AddSingleton<IPlanningEngine, PlanningEngineStub>();
        builder.Services.AddSingleton<ILearningEngine, LearningEngineStub>();
        builder.Services.AddSingleton<IDecisionEngine, DecisionEngineStub>();
        builder.Services.AddSingleton<IWorldModelEngine, WorldModelEngineStub>();
        builder.Services.AddSingleton<ISchedulerEngine, SchedulerEngineStub>();

        // ── Stub Services (placeholder until real implementations) ─
        builder.Services.AddSingleton<IPlanningService, PlanningService>();
        builder.Services.AddSingleton<ILearningService, LearningService>();
        builder.Services.AddSingleton<IDecisionService, DecisionService>();
        builder.Services.AddSingleton<ISchedulerService, SchedulerService>();

        // ── Navigation & Theme ───────────────────────────────
        builder.Services.AddSingleton(_ => new NavigationController(navigationRoot));
        builder.Services.AddSingleton<ThemeController>(_ => new ThemeController(NeonDarkTheme.Instance));

        // ── ViewModels ───────────────────────────────────────
        builder.Services.AddTransient<CoreHudViewModel>();
        builder.Services.AddTransient<MemoryViewModel>();
        builder.Services.AddTransient<CognitionViewModel>();
        builder.Services.AddTransient<VoiceViewModel>();
        builder.Services.AddTransient<AutomationViewModel>();
        builder.Services.AddTransient<PlanningViewModel>();
        builder.Services.AddTransient<DecisionViewModel>();
        builder.Services.AddTransient<LearningViewModel>();
        builder.Services.AddTransient<SchedulerViewModel>();
        builder.Services.AddTransient<SettingsViewModel>();
        builder.Services.AddTransient<KernelViewModel>();
        builder.Services.AddTransient<PluginsViewModel>();
        builder.Services.AddTransient<EventBusViewModel>();

        // ── New ViewModels (FASE 7 pages) ────────────────────
        builder.Services.AddTransient<WorldViewModel>();
        builder.Services.AddTransient<MetricsViewModel>();
        builder.Services.AddTransient<LogsViewModel>();
        builder.Services.AddTransient<DebugViewModel>();
        builder.Services.AddTransient<DeveloperViewModel>();

        // ── Pages (15 HUD Pages) ─────────────────────────────
        builder.Services.AddTransient<MainPage>();
        builder.Services.AddTransient<MemoryPage>();
        builder.Services.AddTransient<BrainPage>();
        builder.Services.AddTransient<VoicePage>();
        builder.Services.AddTransient<AutomationPage>();
        builder.Services.AddTransient<LearningPage>();
        builder.Services.AddTransient<PlanningPage>();
        builder.Services.AddTransient<DecisionPage>();
        builder.Services.AddTransient<SchedulerPage>();
        builder.Services.AddTransient<PluginPage>();
        builder.Services.AddTransient<WorldPage>();
        builder.Services.AddTransient<MetricsPage>();
        builder.Services.AddTransient<LogsPage>();
        builder.Services.AddTransient<DebugPage>();
        builder.Services.AddTransient<SettingsPage>();
        builder.Services.AddTransient<DeveloperPage>();

#if DEBUG
        builder.Logging.AddDebug();
#endif

        var app = builder.Build();
        App.ServiceProvider = app.Services;
        return app;
    }

    /// <summary>
    /// Registers Shell routes for all 15 HUD pages so they can be
    /// navigated to via Shell.Current.GoToAsync("memory") etc.
    /// Called once at startup from App.xaml.cs.
    /// </summary>
    public static void RegisterShellRoutes()
    {
        Routing.RegisterRoute("memory", typeof(MemoryPage));
        Routing.RegisterRoute("brain", typeof(BrainPage));
        Routing.RegisterRoute("voice", typeof(VoicePage));
        Routing.RegisterRoute("automation", typeof(AutomationPage));
        Routing.RegisterRoute("learning", typeof(LearningPage));
        Routing.RegisterRoute("planning", typeof(PlanningPage));
        Routing.RegisterRoute("decision", typeof(DecisionPage));
        Routing.RegisterRoute("scheduler", typeof(SchedulerPage));
        Routing.RegisterRoute("plugin", typeof(PluginPage));
        Routing.RegisterRoute("world", typeof(WorldPage));
        Routing.RegisterRoute("metrics", typeof(MetricsPage));
        Routing.RegisterRoute("logs", typeof(LogsPage));
        Routing.RegisterRoute("debug", typeof(DebugPage));
        Routing.RegisterRoute("settings", typeof(SettingsPage));
        Routing.RegisterRoute("developer", typeof(DeveloperPage));
    }

    public static NavigationNode BuildNavigationTree()
    {
        var root = new NavigationNode("root", "Core", "🧠", "primary");

        // ═══════════════════════════════════════════════════
        //  LEVEL 1 — Main modules (7)
        // ═══════════════════════════════════════════════════

        var ia = NavigationNode.Leaf("ia", "IA", "🤖", "ia");
        var memoria = NavigationNode.Branch("memoria", "Memoria", "🧩", "memory");
        var voz = NavigationNode.Leaf("voz", "Voz", "🎙", "voice");
        var automacoes = NavigationNode.Leaf("automacoes", "Automacoes", "⚡", "automation");
        var agenda = NavigationNode.Leaf("agenda", "Agenda", "📅", "agenda");
        var mundo = NavigationNode.Leaf("mundo", "Mundo", "🌍", "world");
        var sistema = NavigationNode.Branch("sistema", "Sistema", "⚙", "settings");

        // ═══════════════════════════════════════════════════
        //  LEVEL 2 — Memória sub-modules
        // ═══════════════════════════════════════════════════

        var pessoas = NavigationNode.Leaf("pessoas", "Pessoas", "👤", "memory");
        var conversas = NavigationNode.Leaf("conversas", "Conversas", "💬", "memory");
        var arquivos = NavigationNode.Leaf("arquivos", "Arquivos", "📁", "memory");
        var conhecimento = NavigationNode.Branch("conhecimento", "Conhecimento", "📖", "memory");

        // ═══════════════════════════════════════════════════
        //  LEVEL 3 — Conhecimento sub-modules
        // ═══════════════════════════════════════════════════

        var pdfs = NavigationNode.Leaf("pdfs", "PDFs", "📄", "memory");
        var artigos = NavigationNode.Leaf("artigos", "Artigos", "📰", "memory");
        var links = NavigationNode.Leaf("links", "Links", "🔗", "memory");
        var notas = NavigationNode.Leaf("notas", "Notas", "📝", "memory");
        var tags = NavigationNode.Leaf("tags", "Tags", "🏷️", "memory");

        // ═══════════════════════════════════════════════════
        //  LEVEL 2 — Sistema sub-modules
        // ═══════════════════════════════════════════════════

        var plugins = NavigationNode.Leaf("plugins", "Plugins", "🔌", "plugins");
        var metricas = NavigationNode.Leaf("metricas", "Métricas", "📊", "metrics");
        var logs = NavigationNode.Leaf("logs", "Logs", "📋", "logs");
        var debug = NavigationNode.Leaf("debug", "Debug", "🔍", "debug");
        var developer = NavigationNode.Leaf("developer", "Developer", "💻", "developer");

        // ═══════════════════════════════════════════════════
        //  Wire up hierarchy
        // ═══════════════════════════════════════════════════

        root.AddChildren(ia, memoria, voz, automacoes, agenda, mundo, sistema);
        memoria.AddChildren(pessoas, conversas, arquivos, conhecimento);
        conhecimento.AddChildren(pdfs, artigos, links, notas, tags);
        sistema.AddChildren(plugins, metricas, logs, debug, developer);

        return root;
    }
}
