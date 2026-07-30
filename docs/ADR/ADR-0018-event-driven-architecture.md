# ADR-0018: Event Driven Architecture

**Data:** 2026-07-29

**Status:** Aceito

## Contexto

As engines do Jarvis Kernel precisam se comunicar sem acoplamento.
Quando a MemoryEngine cria uma memória, a LearningEngine precisa saber
para atualizar contexto. Quando o Planejador completa uma meta, a
AutomationEngine precisa disparar ações.

No modelo síncrono, cada engine conheceria as outras — acoplamento
forte, difícil de testar, difícil de estender.

## Decisão

Toda comunicação entre engines é **assíncrona e orientada a eventos**.

### Fluxo

```
MemoryEngine ──publish("memory.created")──→ EventBus
                                                │
                          ┌─────────────────────┼────────────────────┐
                          ▼                     ▼                    ▼
                   LearningEngine          CognitionEngine    AutomationEngine
                   (atualiza contexto)   (recalcula foco)   (dispara workflow)
```

### Contrato (Python)

```python
class EventBus:
    async def publish(event: str, data: dict) -> None
    def subscribe(event: str, handler: Callable) -> str  # returns listener_id
    def unsubscribe(listener_id: str) -> None
```

### Contraparte C# obrigatória

```csharp
public interface IEventBus
{
    Task PublishAsync(string eventType, Dictionary<string, object> data);
    string Subscribe(string eventType, Func<string, Dictionary<string, object>, Task> handler);
    void Unsubscribe(string listenerId);
}
```

### Eventos do Sistema (v1)

| Evento | Origem | Consumidores |
|--------|--------|-------------|
| `memory.created` | MemoryEngine | LearningEngine, CognitionEngine |
| `memory.deleted` | MemoryEngine | LearningEngine |
| `memory.searched` | MemoryEngine | LearningEngine |
| `brain.thinking` | CognitionEngine | UI (HUD) |
| `brain.tool_call` | CognitionEngine | UI (HUD) |
| `decision.made` | DecisionEngine | PlanningEngine, AutomationEngine |
| `plan.updated` | PlanningEngine | DecisionEngine, UI (HUD) |
| `plan.completed` | PlanningEngine | AutomationEngine |
| `workflow.started` | AutomationEngine | UI (HUD) |
| `workflow.completed` | AutomationEngine | PlanningEngine |
| `voice.heard` | VoiceEngine | CognitionEngine |
| `voice.speaking` | VoiceEngine | UI (HUD) |
| `learning.insight` | LearningEngine | MemoryEngine, CognitionEngine |

### Tecnologia atual

- **Python**: `asyncio.Queue` + dict de listeners (100% local)
- **C#**: `Channel<Event>` + `Dictionary<string, List<Handler>>`

Futuramente: Redis Streams, NATS JetStream ou Kafka se necessário.

## Consequências

**Positivas:**
- Zero acoplamento entre engines
- Fácil adicionar novos consumidores sem modificar produtores
- Testável (mockar EventBus)
- Auditável (log de todos os eventos)

**Negativas:**
- Complexidade de debugging (fluxo não-linear)
- Latência adicional (assíncrono)
- Eventos órfãos se ninguém consome (não é problema)

## Referências

- [ADR-0017](ADR-0017-jarvis-kernel-architecture.md): Jarvis Kernel Architecture
- `backend-core/app/events/bus.py` (Python)
- `apps/maui/CognitiveHUD/Services/EventBus.cs` (C#)
