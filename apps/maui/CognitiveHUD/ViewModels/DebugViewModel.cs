using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>ViewModel for debug/diagnostics — state inspection, health checks.</summary>
public partial class DebugViewModel : ObservableObject
{
    private readonly KernelService _kernel;
    private readonly GrpcClient _grpc;

    public DebugViewModel(KernelService kernel, GrpcClient grpc)
    {
        _kernel = kernel;
        _grpc = grpc;
    }

    [ObservableProperty]
    private ObservableCollection<DiagnosticEntry> _diagnostics = new();

    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string _status = "—";

    [RelayCommand]
    private async Task RunDiagnosticsAsync()
    {
        IsLoading = true;
        Diagnostics.Clear();
        try
        {
            Diagnostics.Add(new("gRPC", await _grpc.CheckHealthCoreAsync() is not null ? "✅" : "❌"));
            Diagnostics.Add(new("Kernel", _kernel.IsReady ? "✅" : "⏳"));
            Status = $"Diagnóstico concluído — {Diagnostics.Count} verificações";
        }
        catch (Exception ex) { Status = $"Erro: {ex.Message}"; }
        finally { IsLoading = false; }
    }
}

public record DiagnosticEntry(string Component, string Status);
