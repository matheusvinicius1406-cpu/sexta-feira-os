using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class LearningPage : HudBasePage
{
    protected override string ModuleId => "learning";
    protected override string ModuleTitle => "Aprendizado";

    public LearningPage(LearningViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
