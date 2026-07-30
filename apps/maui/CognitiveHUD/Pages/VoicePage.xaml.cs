using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class VoicePage : HudBasePage
{
    protected override string ModuleId => "voice";
    protected override string ModuleTitle => "Voz";

    public VoicePage(VoiceViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
