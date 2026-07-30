# ADR-0014: Comunicação Interna via gRPC

**Data:** 2026-07-29

**Status:** Aceito

## Contexto

O Sexta-Feira OS precisa de um protocolo de comunicação interno entre
a camada de apresentação (MAUI/HUD) e o núcleo cognitivo (Python/Kernel).

Inicialmente usávamos REST (FastAPI), que funciona para request-response
mas é inadequado para:
- Streaming de tokens de IA (chat)
- Streaming bidirecional de áudio (voz)
- Comunicação serviço-a-serviço na futura Service Mesh

## Decisão

Todo o tráfego interno entre a camada de apresentação e os serviços do
kernel usará **gRPC** como protocolo primário.

REST (FastAPI) é mantido exclusivamente para:
- Health checks externos
- Webhooks de automações (n8n)
- Compatibilidade com clientes que não suportam gRPC

### Contratos

Definidos em `.proto` versionados em `shared/protobuf/`:

| Arquivo | Package | Serviços |
|---------|---------|----------|
| `cognitive_core.proto` | `sextafeira.cognitive.v1` | CognitiveCore (chat, memória, ações) |
| `voice_stream.proto` | `sextafeira.voice.v1` | VoiceStream (áudio bidirecional) |
| `automation_events.proto` | `sextafeira.automation.v1` | AutomationService (workflows, eventos, comandos) |

### Stubs

- **Python**: gerados por `backend-core/scripts/generate_protos.sh` → `app/grpc/`
- **C# (.NET MAUI)**: gerados automagicamente via `Grpc.Tools` + `<Protobuf>` no `.csproj`

### Portas

| Protocolo | Porta | Uso |
|-----------|-------|-----|
| gRPC | 50051 | Comunicação interna (MAUI ↔ Kernel) |
| REST | 8000 | FastAPI (webhooks, health, clientes REST) |

## Consequências

**Positivas:**
- Streaming nativo para chat e voz
- Tipos fortes via Protobuf (menos erros de runtime)
- Geração automática de stubs para Python e C#
- Mesmo contrato para todas as linguagens
- Base pronta para Service Mesh futura

**Negativas:**
- Clientes sem suporte a gRPC precisam de REST (mantido)
- Complexidade adicional de setup (protoc, stubs)
- Ferramentas de debugging mais especializadas (grpcurl, etc.)

## Alternativas Consideradas

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| REST puro | Sem streaming bidirecional nativo |
| WebSocket | Sem contratos tipados, sem geração de stubs |
| RabbitMQ/MQTT | Overkill para comunicação local direta |

## Referências

- [ADR-0015](ADR-0015-thin-gateway.md): Thin Gateway Architecture
- `shared/protobuf/cognitive_core.proto`
- `backend-core/app/grpc/server.py`
