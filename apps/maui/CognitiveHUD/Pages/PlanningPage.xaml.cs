using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class PlanningPage : HudBasePage
{
    protected override string ModuleId => "planning";
    protected override string ModuleTitle => "Planejamento";

    public PlanningPage(PlanningViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
