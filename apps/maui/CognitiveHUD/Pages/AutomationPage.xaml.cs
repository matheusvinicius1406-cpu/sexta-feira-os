using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class AutomationPage : HudBasePage
{
    protected override string ModuleId => "automation";
    protected override string ModuleTitle => "Automações";

    public AutomationPage(AutomationViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
