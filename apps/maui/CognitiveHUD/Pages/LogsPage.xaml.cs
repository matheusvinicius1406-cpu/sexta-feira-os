using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class LogsPage : HudBasePage
{
    protected override string ModuleId => "logs";
    protected override string ModuleTitle => "Logs";

    public LogsPage(LogsViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
