using Microsoft.Extensions.Logging;
using SkiaSharp.Views.Maui.Controls.Hosting;
using SextaFeira.CognitiveHUD.Services;
using SextaFeira.CognitiveHUD.ViewModels;
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

        // ── Build the navigation tree root ─────────────────
        var navigationRoot = BuildNavigationTree();

        // ── Services ─────────────────────────────────────────
        builder.Services.AddSingleton<ApiClient>();
        builder.Services.AddSingleton(_ => new NavigationController(navigationRoot));
        // AnimationController is used internally; registered for future sub-controller use
        // builder.Services.AddSingleton<AnimationController>();
        builder.Services.AddSingleton<ThemeController>(_ => new ThemeController(NeonDarkTheme.Instance));

        // ── ViewModels ────────────────────────────────────────
        builder.Services.AddTransient<CoreHudViewModel>();

        // ── Pages ─────────────────────────────────────────────
        builder.Services.AddTransient<MainPage>();

#if DEBUG
        builder.Logging.AddDebug();
#endif

        return builder.Build();
    }

    /// <summary>
    /// Builds the navigation tree used by NavigationController.
    /// Centralized so both DI registration and ViewModel can reference it.
    /// </summary>
    public static NavigationNode BuildNavigationTree()
    {
        var root = new NavigationNode("root", "Core", "🧠", "primary");

        // Level 1 modules
        var ia = NavigationNode.Leaf("ia", "IA", "🤖", "ia");
        var memoria = NavigationNode.Branch("memoria", "Memória", "🧩", "memory");
        var agenda = NavigationNode.Leaf("agenda", "Agenda", "📅", "agenda");
        var biblioteca = NavigationNode.Leaf("biblioteca", "Biblioteca", "📚", "library");
        var automacoes = NavigationNode.Leaf("automacoes", "Automações", "⚡", "automation");
        var dispositivos = NavigationNode.Leaf("dispositivos", "Dispositivos", "📱", "devices");
        var configuracoes = NavigationNode.Leaf("configuracoes", "Config", "⚙️", "settings");

        // Level 2 — Memory sub-modules
        var pessoas = NavigationNode.Leaf("pessoas", "Pessoas", "👤", "memory");
        var conversas = NavigationNode.Leaf("conversas", "Conversas", "💬", "memory");
        var arquivos = NavigationNode.Leaf("arquivos", "Arquivos", "📁", "memory");
        var conhecimento = NavigationNode.Branch("conhecimento", "Conhecimento", "📖", "memory");

        // Level 3 — Knowledge sub-modules
        var pdfs = NavigationNode.Leaf("pdfs", "PDFs", "📄", "memory");
        var artigos = NavigationNode.Leaf("artigos", "Artigos", "📰", "memory");
        var links = NavigationNode.Leaf("links", "Links", "🔗", "memory");
        var notas = NavigationNode.Leaf("notas", "Notas", "📝", "memory");
        var tags = NavigationNode.Leaf("tags", "Tags", "🏷️", "memory");

        // Wire up hierarchy
        root.AddChildren(ia, memoria, agenda, biblioteca, automacoes, dispositivos, configuracoes);
        memoria.AddChildren(pessoas, conversas, arquivos, conhecimento);
        conhecimento.AddChildren(pdfs, artigos, links, notas, tags);

        return root;
    }
}
