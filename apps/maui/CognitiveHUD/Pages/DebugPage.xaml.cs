using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class DebugPage : HudBasePage
{
    protected override string ModuleId => "debug";
    protected override string ModuleTitle => "Debug";

    public DebugPage(DebugViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
