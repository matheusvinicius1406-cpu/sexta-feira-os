using System.Net.Http.Json;

namespace SextaFeira.CognitiveHUD.Services;

// ── MarketplaceEntry ─────────────────────────────────────

/// <summary>A plugin listing from the marketplace.</summary>
public record MarketplaceEntry(
    string PluginId,
    string DisplayName,
    string Version,
    string Author,
    string Description,
    string DownloadUrl,
    string Checksum,
    IReadOnlyList<string>? Dependencies = null,
    IReadOnlyList<string>? Permissions = null);

// ── PluginMarketplaceClient ──────────────────────────────

/// <summary>Client for discovering and downloading plugins from a remote registry.</summary>
public class PluginMarketplaceClient
{
    private const string DefaultRegistry = "https://plugins.sexta-feira.local";

    private readonly HttpClient _http;
    private readonly string _registryUrl;
    private readonly Dictionary<string, MarketplaceEntry> _cache = new();

    public PluginMarketplaceClient(HttpClient? http = null, string? registryUrl = null)
    {
        _http = http ?? new HttpClient();
        _registryUrl = registryUrl ?? DefaultRegistry;
    }

    /// <summary>List all available plugins from the marketplace.</summary>
    public async Task<IReadOnlyList<MarketplaceEntry>> ListAvailableAsync()
    {
        try
        {
            var response = await _http.GetFromJsonAsync<MarketplaceResponse>(
                $"{_registryUrl}/api/v1/plugins");
            if (response?.Plugins is not null)
            {
                _cache.Clear();
                foreach (var entry in response.Plugins)
                    _cache[entry.PluginId] = entry;
                return response.Plugins.ToList().AsReadOnly();
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Marketplace] Unavailable: {ex.Message}");
        }
        return Array.Empty<MarketplaceEntry>();
    }

    /// <summary>Search cached marketplace entries.</summary>
    public IReadOnlyList<MarketplaceEntry> Search(string query)
    {
        var q = query.ToLowerInvariant();
        return _cache.Values
            .Where(e => e.PluginId.Contains(q) || e.DisplayName.Contains(q) || e.Description.Contains(q))
            .ToList().AsReadOnly();
    }
}

/// <summary>Response wrapper from marketplace API.</summary>
internal record MarketplaceResponse(IReadOnlyList<MarketplaceEntry> Plugins);
