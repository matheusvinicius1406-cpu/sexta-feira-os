using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SextaFeira.CognitiveHUD.Models;
using SextaFeira.CognitiveHUD.Services;

namespace SextaFeira.CognitiveHUD.ViewModels;

/// <summary>
/// ViewModel for memory operations — CRUD, search, and graph visualization.
/// Mirrors Python MemoryAdapter + MemoryService in the C# layer.
/// </summary>
public partial class MemoryViewModel : ObservableObject
{
    private readonly IMemoryService _memoryService;
    private readonly IEventBus _eventBus;

    public MemoryViewModel(IMemoryService memoryService, IEventBus eventBus)
    {
        _memoryService = memoryService;
        _eventBus = eventBus;
    }

    // ── Observable State ─────────────────────────────────

    [ObservableProperty]
    private ObservableCollection<MemoryNode> _memories = new();

    [ObservableProperty]
    private MemoryNode? _selectedMemory;

    [ObservableProperty]
    private MemoryGraph? _memoryGraph;

    [ObservableProperty]
    private string _searchQuery = "";

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _errorMessage;

    [ObservableProperty]
    private int _totalResults;

    // ── Commands ─────────────────────────────────────────

    [RelayCommand]
    private async Task LoadGraphAsync()
    {
        IsLoading = true;
        ErrorMessage = null;
        try
        {
            MemoryGraph = await _memoryService.GetMemoryGraphAsync(50);
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao carregar grafo: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task SearchAsync()
    {
        if (string.IsNullOrWhiteSpace(SearchQuery)) return;

        IsLoading = true;
        ErrorMessage = null;
        try
        {
            var result = await _memoryService.SearchMemoryAsync(SearchQuery, 20);
            Memories.Clear();
            foreach (var node in result.Results)
                Memories.Add(node);
            TotalResults = result.Total;
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro na busca: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task CreateMemoryAsync(string content)
    {
        if (string.IsNullOrWhiteSpace(content)) return;

        IsLoading = true;
        ErrorMessage = null;
        try
        {
            var node = await _memoryService.CreateMemoryAsync(content);
            if (node is not null)
                Memories.Insert(0, node);
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao criar memória: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task DeleteMemoryAsync(string memoryId)
    {
        IsLoading = true;
        ErrorMessage = null;
        try
        {
            var success = await _memoryService.DeleteMemoryAsync(memoryId);
            if (success)
            {
                var item = Memories.FirstOrDefault(m => m.Id == memoryId);
                if (item is not null)
                    Memories.Remove(item);
            }
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao deletar: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task LinkMemoriesAsync(MemoryLinkRequest request)
    {
        IsLoading = true;
        ErrorMessage = null;
        try
        {
            await _memoryService.LinkMemoriesAsync(
                request.SourceId, request.TargetId, request.Relation);
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Erro ao conectar: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }
}
