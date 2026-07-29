using System.Net.Http.Json;
using System.Text.Json.Serialization;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>
/// HTTP client for communicating with the Sexta-Feira cognitive core backend (Python/FastAPI).
/// All communication happens over local network (REST today, gRPC in future phases).
/// </summary>
public class ApiClient
{
    private readonly HttpClient _httpClient;
    private string _baseUrl = "http://127.0.0.1:8000";

    // ── Configuration ──────────────────────────────────────
    public string BaseUrl
    {
        get => _baseUrl;
        set => _baseUrl = value.TrimEnd('/');
    }

    public TimeSpan Timeout
    {
        get => _httpClient.Timeout;
        set => _httpClient.Timeout = value;
    }

    // ── Auth token ─────────────────────────────────────────
    private string? _authToken;

    public void SetAuthToken(string? token)
    {
        _authToken = token;
    }

    public ApiClient()
    {
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(10),
        };
    }

    // ── Health ─────────────────────────────────────────────
    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync($"{_baseUrl}/api/v1/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    // ── Auth ───────────────────────────────────────────────
    public async Task<AuthResult?> LoginAsync(string email, string password)
    {
        try
        {
            var request = new { email, password };
            var response = await _httpClient.PostAsJsonAsync(
                $"{_baseUrl}/api/v1/auth/login", request);

            if (!response.IsSuccessStatusCode)
                return null;

            return await response.Content.ReadFromJsonAsync<AuthResult>();
        }
        catch
        {
            return null;
        }
    }

    // ── Chat ───────────────────────────────────────────────
    public async Task<ChatResult?> SendMessageAsync(string message, string? conversationId = null)
    {
        try
        {
            var request = new
            {
                message,
                conversation_id = conversationId,
            };

            var httpRequest = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/api/v1/chat")
            {
                Content = JsonContent.Create(request),
            };

            if (!string.IsNullOrEmpty(_authToken))
            {
                httpRequest.Headers.Authorization =
                    new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _authToken);
            }

            var response = await _httpClient.SendAsync(httpRequest);

            if (!response.IsSuccessStatusCode)
                return null;

            return await response.Content.ReadFromJsonAsync<ChatResult>();
        }
        catch
        {
            return null;
        }
    }

    // ── Memory ─────────────────────────────────────────────
    public async Task<MemorySearchResult?> SearchMemoryAsync(string query)
    {
        try
        {
            var request = new { query, limit = 10 };
            var response = await _httpClient.PostAsJsonAsync(
                $"{_baseUrl}/api/v1/memory/recall", request);

            if (!response.IsSuccessStatusCode)
                return null;

            return await response.Content.ReadFromJsonAsync<MemorySearchResult>();
        }
        catch
        {
            return null;
        }
    }

    // ── Voice ──────────────────────────────────────────────
    public async Task<VoiceStatusResult?> GetVoiceStatusAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync($"{_baseUrl}/api/v1/voice/status");
            if (!response.IsSuccessStatusCode)
                return null;

            return await response.Content.ReadFromJsonAsync<VoiceStatusResult>();
        }
        catch
        {
            return null;
        }
    }
}

// ── DTOs ──────────────────────────────────────────────────

public record AuthResult(
    [property: JsonPropertyName("access_token")] string AccessToken,
    [property: JsonPropertyName("token_type")] string TokenType);

public record ChatResult(
    [property: JsonPropertyName("reply")] string Reply,
    [property: JsonPropertyName("conversation_id")] string ConversationId);

public record MemorySearchResult(
    [property: JsonPropertyName("results")] List<MemoryItem> Results);

public record MemoryItem(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("content")] string Content,
    [property: JsonPropertyName("title")] string? Title,
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("importance")] float Importance);

public record VoiceStatusResult(
    [property: JsonPropertyName("stt_available")] bool SttAvailable,
    [property: JsonPropertyName("tts_available")] bool TtsAvailable);
