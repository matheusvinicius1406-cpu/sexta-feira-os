# ADR-0017: Jarvis Kernel Architecture

**Data:** 2026-07-29

**Status:** Aceito

## Contexto

O Kernel do Sexta-Feira OS era um monolito com múltiplas responsabilidades
acopladas. Com a FASE 5 (Thin Gateway + Adapters), o gateway foi limpo,
mas o núcleo ainda precisa de uma estrutura de **Engines** com interfaces
claras e lifecycle gerenciado.

## Decisão

O Kernel é refatorado em **7 Engines independentes**, cada uma com:

- Interface pública (`I<Nome>Engine`)
- Implementação concreta
- Ciclo de vida (init → ready → stop)
- Eventos próprios (publicados no EventBus)
- Contraparte C# (.NET MAUI) com interface idêntica

### Estrutura

```
JarvisKernel
├── MemoryEngine      → Persistência, recall, grafo, wikilinks
├── CognitionEngine   → LLM, streaming, tool calling
├── DecisionEngine    → Escolhas sob restrições, auditável
├── PlanningEngine    → Planos, metas, progresso
├── AutomationEngine  → n8n, workflows, agendamentos
├── VoiceEngine       → STT, TTS, VAD, áudio bidirecional
└── LearningEngine    → Extração de conhecimento, auto-aprendizado
```

### Contrato da Engine (Python)

```python
class IEngine(ABC):
    name: str
    async def initialize(self) -> None
    async def health(self) -> bool
    async def shutdown(self) -> None
```

### Contraparte C# obrigatória

```csharp
public interface IEngine
{
    string Name { get; }
    Task<bool> HealthAsync();
    Task InitializeAsync();
    Task ShutdownAsync();
}
```

## Consequências

**Positivas:**
- Cada engine testável isoladamente
- Substituível (trocar implementação sem afetar outras engines)
- Lifecycle claro (start/stop orquestrado)
- Mesma interface em Python e C# — contratos bilíngues

**Negativas:**
- Mais arquivos (cada engine vira ~4 arquivos: interface Python + impl + interface C# + impl)
- Coordenação entre engines requer EventBus (ADR-0018)

## Referências

- [ADR-0018](ADR-0018-event-driven-architecture.md): Event Driven Architecture
- `backend-core/app/engines/` (Python)
- `apps/maui/CognitiveHUD/Engines/` (C#)
