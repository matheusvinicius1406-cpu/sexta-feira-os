using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class DecisionPage : HudBasePage
{
    protected override string ModuleId => "decision";
    protected override string ModuleTitle => "Decisões";

    public DecisionPage(DecisionViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
