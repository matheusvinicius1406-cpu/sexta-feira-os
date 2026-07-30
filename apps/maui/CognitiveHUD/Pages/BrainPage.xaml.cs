using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class BrainPage : HudBasePage
{
    private readonly CognitionViewModel _vm;

    protected override string ModuleId => "brain";
    protected override string ModuleTitle => "Cognição";

    public BrainPage(CognitionViewModel vm)
    {
        _vm = vm;
        InitializeComponent(); // XAML defines Content
        BindingContext = _vm;
    }
}
