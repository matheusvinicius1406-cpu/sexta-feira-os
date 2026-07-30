using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class MemoryPage : HudBasePage
{
    private readonly MemoryViewModel _vm;

    protected override string ModuleId => "memory";
    protected override string ModuleTitle => "Memória";

    public MemoryPage(MemoryViewModel vm)
    {
        _vm = vm;
        InitializeComponent(); // XAML defines Content = grid with HudCanvas + stats
        BindingContext = _vm;

    }
}
