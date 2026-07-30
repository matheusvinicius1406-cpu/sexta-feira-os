using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly GrpcClient _grpc;

    public SettingsViewModel(GrpcClient grpc)
    {
        _grpc = grpc;
    }

    [ObservableProperty] private string _kernelEndpoint = "http://127.0.0.1:50051";
    [ObservableProperty] private bool _isConnected;
    [ObservableProperty] private string? _connectionStatus = "Desconectado";
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;

    [RelayCommand]
    private async Task CheckConnectionAsync()
    {
        IsLoading = true;
        ConnectionStatus = "Conectando...";
        try
        {
            var health = await _grpc.CheckHealthCoreAsync();
            IsConnected = health is not null;
            ConnectionStatus = IsConnected ? "Conectado" : "Offline";
        }
        catch
        {
            IsConnected = false;
            ConnectionStatus = "Erro de conexão";
        }
        finally
        {
            IsLoading = false;
        }
    }
}
