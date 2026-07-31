namespace SextaFeira.UIEngine.Reactor;

/// <summary>External events that can change what the assistant is doing.</summary>
public enum BrainSignal { Wake, Command, Navigate }

/// <summary>
/// Drives <see cref="ReactorState"/> from the assistant's own lifecycle.
///
/// Nothing here is a manual switch: a state arrives because something
/// happened — a wake word, a command, a background job, a dropped link — or
/// because a conversation is running its natural course. The status chip
/// reflects; it never commands. See docs/design-system/05-MOVIMENTO.md §1.
///
/// Until the kernel is wired in, the scripted timeline below stands in for
/// those signals so every state still appears on its own. Replacing it with
/// EventBus subscriptions changes nothing else.
/// </summary>
public sealed class ArcBrain
{
    private readonly ReactorModel _model;
    private readonly Action<ReactorState>? _onStateChanged;
    private readonly Action<string>? _onCaption;

    private float _timer;
    private int _step;

    public ArcBrain(ReactorModel model,
                    Action<ReactorState>? onStateChanged = null,
                    Action<string>? onCaption = null)
    {
        _model = model;
        _onStateChanged = onStateChanged;
        _onCaption = onCaption;
    }

    /// <summary>A plausible day in the life, so no state stays unseen.</summary>
    private static readonly (ReactorState State, float Seconds, string? Caption)[] Timeline =
    {
        (ReactorState.Idle,      8f,  null),
        (ReactorState.Listening, 3.6f, "arc, qual o status do núcleo?"),
        (ReactorState.Thinking,  2.4f, null),
        (ReactorState.Speaking,  4.6f, "Reator estável. Carga do núcleo em 8 por cento."),
        (ReactorState.Idle,      6f,  null),
        (ReactorState.Thinking,  1.8f, null),
        (ReactorState.Idle,      7f,  null),
        (ReactorState.Warning,   2.6f, null),
        (ReactorState.Idle,      8f,  null),
        (ReactorState.Listening, 3.2f, "quantos agentes estão rodando?"),
        (ReactorState.Thinking,  2.8f, null),
        (ReactorState.Speaking,  5f,   "Três agentes ativos, fila vazia."),
        (ReactorState.Idle,      9f,  null),
        (ReactorState.Offline,   3f,  null),
        (ReactorState.Error,     2f,  null),
        (ReactorState.Idle,      6f,  null),
    };

    public void Tick(float dt)
    {
        _timer -= dt;
        if (_timer > 0f) return;

        var (state, seconds, caption) = Timeline[_step % Timeline.Length];
        _step++;
        _timer = seconds;

        if (_model.State != state)
        {
            _model.State = state;
            _onStateChanged?.Invoke(state);
        }
        if (caption is not null) _onCaption?.Invoke(caption);
    }

    /// <summary>A real signal from outside — the only other way state moves.</summary>
    public void Observe(BrainSignal signal)
    {
        switch (signal)
        {
            case BrainSignal.Wake:
                Jump(ReactorState.Listening, 3.5f);
                break;
            case BrainSignal.Command:
                Jump(ReactorState.Thinking, 2f);
                break;
            case BrainSignal.Navigate:
                // Opening a module makes the assistant work briefly, but only
                // when it is otherwise idle — never interrupt a conversation.
                if (_model.State == ReactorState.Idle) Jump(ReactorState.Thinking, 1f);
                break;
        }
    }

    private void Jump(ReactorState state, float seconds)
    {
        _model.State = state;
        _timer = seconds;
        _onStateChanged?.Invoke(state);
    }
}
