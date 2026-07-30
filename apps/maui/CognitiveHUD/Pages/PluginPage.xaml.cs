using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class PluginPage : HudBasePage
{
    protected override string ModuleId => "plugin";
    protected override string ModuleTitle => "Plugins";

    public PluginPage(PluginsViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
