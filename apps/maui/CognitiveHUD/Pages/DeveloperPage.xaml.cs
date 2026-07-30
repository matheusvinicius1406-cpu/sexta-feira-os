using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class DeveloperPage : HudBasePage
{
    protected override string ModuleId => "developer";
    protected override string ModuleTitle => "Developer";

    public DeveloperPage(DeveloperViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
