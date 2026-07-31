using CommunityToolkit.Maui.Media;
using SextaFeira.UIEngine.Reactor;

namespace SextaFeira.CognitiveHUD.Services;

/// <summary>What the voice loop is doing right now.</summary>
public enum VoicePhase { Idle, Listening, Thinking, Speaking, Denied, Unavailable }

/// <summary>
/// Hearing and speaking, wired to the reactor.
///
/// This is the real source of <see cref="ReactorState"/> during a
/// conversation: the microphone opening is what makes the core pulse, the
/// model working is what accelerates the rings, and the first spoken word is
/// what brightens it. Nothing here is triggered by a control.
///
/// Speech recognition and synthesis are on-device — no audio leaves the
/// machine, which is the whole point of a local kernel.
/// </summary>
public sealed class ArcVoiceLoop : IAsyncDisposable
{
    private readonly ISpeechToText _stt;
    private readonly IEventBus _bus;
    private CancellationTokenSource? _listenCts;

    /// <summary>Fired whenever the phase changes, so the HUD can follow.</summary>
    public event Action<VoicePhase>? PhaseChanged;

    /// <summary>Fired with recognised speech, then with the spoken reply.</summary>
    public event Action<string, bool>? Transcript;

    public VoicePhase Phase { get; private set; } = VoicePhase.Idle;
    public string LastHeard { get; private set; } = string.Empty;
    public string LastSpoken { get; private set; } = string.Empty;

    public ArcVoiceLoop(ISpeechToText stt, IEventBus bus)
    {
        _stt = stt;
        _bus = bus;
    }

    /// <summary>Appends to the same log the startup crash handler uses.</summary>
    private static void Log(string message) => MauiProgram.LogStartupCrash("voice", message);

    /// <summary>
    /// Probes both halves of the voice stack and writes what it finds.
    ///
    /// Audio failures are invisible from the outside — a silent app looks
    /// identical whether the synthesiser is missing, the microphone is
    /// blocked, or the turn never started. This turns that into a readable
    /// answer on disk.
    /// </summary>
    public async Task SelfTestAsync()
    {
        // ── Synthesis ───────────────────────────────────────
        try
        {
            var locales = (await TextToSpeech.Default.GetLocalesAsync()).ToList();
            Log($"TTS locales: {locales.Count}");
            if (locales.Count > 0)
            {
                var sample = string.Join(", ", locales.Take(5).Select(l => l.Language + "/" + l.Name));
                Log($"TTS sample: {sample}");
            }
            else
            {
                Log("TTS: nenhuma voz instalada — SpeakAsync nao produzira som");
            }
        }
        catch (Exception ex) { Log($"TTS FALHOU: {ex.GetType().Name}: {ex.Message}"); }

        // Speak on boot. This is the proof that synthesis works on its own —
        // it used to be reachable only after a successful recognition, so a
        // broken recogniser made the whole assistant mute.
        await SpeakAsync("Arc online. Sistemas nominais.");

        // ── Recognition ─────────────────────────────────────
        try
        {
            var granted = await _stt.RequestPermissions(CancellationToken.None);
            Log($"STT permissao: {granted}");
        }
        catch (Exception ex) { Log($"STT FALHOU: {ex.GetType().Name}: {ex.Message}"); }
    }

    private void SetPhase(VoicePhase phase)
    {
        if (Phase == phase) return;
        Phase = phase;
        PhaseChanged?.Invoke(phase);
    }

    /// <summary>Maps a voice phase onto what the reactor should show.</summary>
    public static ReactorState ToReactorState(VoicePhase phase) => phase switch
    {
        VoicePhase.Listening => ReactorState.Listening,
        VoicePhase.Thinking => ReactorState.Thinking,
        VoicePhase.Speaking => ReactorState.Speaking,
        VoicePhase.Denied or VoicePhase.Unavailable => ReactorState.Warning,
        _ => ReactorState.Idle,
    };

    /// <summary>
    /// Opens the microphone and runs one turn: listen, think, speak.
    /// Safe to call while already listening — the second call is ignored.
    /// </summary>
    public async Task ListenOnceAsync(Func<string, Task<string>> respond)
    {
        if (Phase is VoicePhase.Listening or VoicePhase.Thinking or VoicePhase.Speaking)
            return;

        Log("turno iniciado");
        bool granted;
        try { granted = await _stt.RequestPermissions(CancellationToken.None); }
        catch (Exception ex) { Log($"permissao lancou: {ex.GetType().Name}: {ex.Message}"); SetPhase(VoicePhase.Unavailable); return; }
        if (!granted) { Log("permissao negada"); SetPhase(VoicePhase.Denied); return; }

        _listenCts = new CancellationTokenSource();
        var heard = string.Empty;

        try
        {
            SetPhase(VoicePhase.Listening);
            await _bus.PublishAsync("voice.listening", new Dictionary<string, object>());

            // ListenAsync resolves when the recogniser decides the utterance
            // ended; the partial handler is what makes the HUD feel live
            // rather than only reacting once speech is over.
            var result = await _stt.ListenAsync(
                System.Globalization.CultureInfo.CurrentCulture,
                new Progress<string>(partial =>
                {
                    heard = partial;
                    Transcript?.Invoke(partial, true);
                }),
                _listenCts.Token);

            heard = result.IsSuccessful ? result.Text : heard;
        }
        catch (OperationCanceledException) { /* user stopped the turn */ }
        catch (Exception ex)
        {
            // No recogniser on this platform, or the engine failed to start.
            Log($"ListenAsync falhou: {ex.GetType().Name}: {ex.Message}");
            SetPhase(VoicePhase.Unavailable);
            return;
        }

        if (string.IsNullOrWhiteSpace(heard)) { SetPhase(VoicePhase.Idle); return; }

        Log($"ouvido: {heard}");
        LastHeard = heard;
        Transcript?.Invoke(heard, true);
        await _bus.PublishAsync("voice.heard", new Dictionary<string, object>
        {
            ["transcript"] = heard.Length > 200 ? heard[..200] : heard,
        });

        SetPhase(VoicePhase.Thinking);
        string reply;
        try { reply = await respond(heard); }
        catch (Exception ex) { reply = $"Falhei ao responder: {ex.Message}"; }

        await SpeakAsync(reply);
        SetPhase(VoicePhase.Idle);
    }

    /// <summary>Speaks a line and holds the Speaking phase until it finishes.</summary>
    public async Task SpeakAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return;

        Log($"falando: {text}");
        LastSpoken = text;
        SetPhase(VoicePhase.Speaking);
        Transcript?.Invoke(text, false);
        await _bus.PublishAsync("voice.speaking", new Dictionary<string, object>
        {
            ["text_preview"] = text.Length > 200 ? text[..200] : text,
        });

        try
        {
            var locale = await PreferredLocaleAsync();
            await TextToSpeech.Default.SpeakAsync(text, new SpeechOptions
            {
                Locale = locale,
                Pitch = 1.0f,
                Volume = 1.0f,
            });
        }
        catch (Exception ex)
        {
            // No synthesiser installed. The reply still reached the HUD as
            // text, so the turn is degraded rather than lost.
            Log($"SpeakAsync falhou: {ex.GetType().Name}: {ex.Message}");
            SetPhase(VoicePhase.Unavailable);
        }
    }

    /// <summary>
    /// Picks the assistant's voice.
    ///
    /// Preference order: a male voice in the system language, then any voice
    /// in that language, then anything installed. Male first because the
    /// assistant has a name and a character — falling back to whatever the OS
    /// lists first makes it sound like a different program each machine.
    /// On this box that resolves to Microsoft Daniel (pt-BR).
    /// </summary>
    private static readonly string[] MaleVoiceHints =
        { "daniel", "david", "mark", "guy", "ricardo", "male" };

    private static Locale? _cachedLocale;
    private static bool _localeResolved;

    private static async Task<Locale?> PreferredLocaleAsync()
    {
        if (_localeResolved) return _cachedLocale;
        _localeResolved = true;

        try
        {
            var wanted = System.Globalization.CultureInfo.CurrentCulture.TwoLetterISOLanguageName;
            var locales = (await TextToSpeech.Default.GetLocalesAsync()).ToList();
            Log($"vozes disponiveis: {locales.Count}");
            foreach (var l in locales.Take(8)) Log($"  voz: {l.Name} [{l.Language}-{l.Country}]");

            bool InLanguage(Locale l) =>
                l.Language.StartsWith(wanted, StringComparison.OrdinalIgnoreCase);
            bool SoundsMale(Locale l) =>
                MaleVoiceHints.Any(h => l.Name.Contains(h, StringComparison.OrdinalIgnoreCase));

            _cachedLocale = locales.FirstOrDefault(l => InLanguage(l) && SoundsMale(l))
                         ?? locales.FirstOrDefault(InLanguage)
                         ?? locales.FirstOrDefault(SoundsMale)
                         ?? locales.FirstOrDefault();

            Log($"voz escolhida: {_cachedLocale?.Name ?? "(padrao do sistema)"}");
        }
        catch (Exception ex)
        {
            Log($"GetLocalesAsync falhou: {ex.GetType().Name}: {ex.Message}");
            _cachedLocale = null;
        }
        return _cachedLocale;
    }

    public void Stop() => _listenCts?.Cancel();

    public ValueTask DisposeAsync()
    {
        _listenCts?.Cancel();
        _listenCts?.Dispose();
        return ValueTask.CompletedTask;
    }
}
