using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class SchedulerPage : HudBasePage
{
    protected override string ModuleId => "scheduler";
    protected override string ModuleTitle => "Agenda";

    public SchedulerPage(SchedulerViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
