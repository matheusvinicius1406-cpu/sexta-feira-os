namespace SextaFeira.CognitiveHUD.Models;

/// <summary>Request to dispatch an action to a device.</summary>
public record ActionRequest(
    string Device,
    string Action,
    Dictionary<string, string>? Parameters = null);

/// <summary>Response from dispatching an action.</summary>
public record ActionResult(
    string CommandId,
    bool Accepted,
    string? Error = null);

/// <summary>Known device identifiers for action dispatch.</summary>
public static class KnownDevices
{
    public const string Phone = "celular";
    public const string Pc = "computador";
    public const string Home = "casa";
    public const string Car = "carro";
}
