using SextaFeira.CognitiveHUD.ViewModels;

namespace SextaFeira.CognitiveHUD.Pages;

public partial class MetricsPage : HudBasePage
{
    protected override string ModuleId => "metrics";
    protected override string ModuleTitle => "Métricas";

    public MetricsPage(MetricsViewModel vm)
    {
        InitializeComponent();
        BindingContext = vm;
    }
}
