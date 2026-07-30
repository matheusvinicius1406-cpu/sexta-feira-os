using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class SettingsPage : HudBasePage
{
    protected override string ModuleId => "settings";
    protected override string ModuleTitle => "Configurações";

    public SettingsPage(SettingsViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
