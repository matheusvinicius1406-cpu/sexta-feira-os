using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class WorldPage : HudBasePage
{
    protected override string ModuleId => "world";
    protected override string ModuleTitle => "Mundo";

    public WorldPage(WorldViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
