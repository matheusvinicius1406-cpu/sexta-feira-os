# ADR-0016: Domain Adapter Layer

**Data:** 2026-07-29

**Status:** Aceito

## Contexto

Os serviços gRPC originais importavam diretamente do Kernel
(`app.core.di`), criavam sessões de banco (`SessionLocal`) e
consultavam modelos SQLAlchemy (`Owner`, `Memory`). Isso gerava
acoplamento forte entre a camada de transporte e o domínio.

Qualquer mudança no domínio — nova versão do SQLAlchemy, mudança
no schema do banco, refatoração do Kernel — exigia mudanças nos
serviços gRPC.

## Decisão

Toda comunicação entre o gateway (gRPC/REST) e o domínio passa
por uma **camada de adaptadores** em `app/adapters/`.

### Estrutura

```
app/
├── adapters/                    ← CAMADA DE ADAPTERS
│   ├── __init__.py
│   ├── memory_adapter.py        ← PersistentMemory + DB + Owner
│   ├── cognition_adapter.py     ← Cognition + LocalBrain
│   ├── voice_adapter.py         ← VoiceBox (STT/TTS)
│   └── automation_adapter.py    ← N8nClient + EventBus + ActionBus
├── grpc/                        ← THIN GATEWAY (só conhece adapters)
│   ├── server.py
│   ├── cognitive_service.py
│   ├── voice_service.py
│   └── automation_service.py
├── brain/                       ← DOMAIN (não sabe que gRPC existe)
├── voice/
├── automation/
├── core/
├── db/
└── models/
```

### Regras

1. **Gateway (grpc/)**: importa APENAS de `app.adapters.*`. Proibido
   importar de `app.core.di`, `app.db.database`, `app.models.models`.

2. **Adapters (adapters/)**: única camada que pode importar do Kernel,
   DB e Models. Gerencia sessões, owner lookup, tratamento de erros.

3. **Domínio (brain/, voice/, etc.)**: não sabe que gRPC, REST ou
   adapters existem. Código puro de negócio.

### Contrato de cada adapter

| Adapter | Métodos principais | Domínio encapsulado |
|---------|-------------------|---------------------|
| `MemoryAdapter` | `create`, `get_by_id`, `delete`, `search`, `link`, `unlink`, `get_neighbours`, `get_graph` | `PersistentMemory`, `Session`, `Owner` |
| `CognitionAdapter` | `check_health`, `chat_stream` | `Cognition`, `LocalBrain` |
| `VoiceAdapter` | `transcribe`, `speak`, `chat` | `VoiceBox`, `STT`, `TTS` |
| `AutomationAdapter` | `trigger_workflow`, `list_workflows`, `stream_events`, `stream_device_commands`, `report_command_result` | `N8nClient`, `EventBus`, `ActionBus` |

## Consequências

**Positivas:**
- Domínio protegido de mudanças na camada de transporte
- Adaptadores podem ser testados isoladamente
- Cada adapter pode evoluir para um microsserviço independente (FASE 6+)
- Gateway trocável (gRPC → REST sem afetar domínio)

**Negativas:**
- Código adicional de "passagem" (wrapper methods)
- Adaptadores precisam ser atualizados quando o domínio muda
- Indireção pode dificultar debug se não bem documentada

## Referências

- [ADR-0014](ADR-0014-grpc-internal-communication.md): gRPC Internal Communication
- [ADR-0015](ADR-0015-thin-gateway.md): Thin Gateway Architecture
- `backend-core/app/adapters/`
