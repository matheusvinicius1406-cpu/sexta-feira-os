# ADR-0015: Thin Gateway Architecture

**Data:** 2026-07-29

**Status:** Aceito

## Contexto

O gateway gRPC (implementado em `app/grpc/server.py`) é o ponto único
de entrada para clientes externos (MAUI, dispositivos, outros serviços).

Ele precisa ser rápido, resiliente e, acima de tudo, **não conter
lógica de negócio** — caso contrário, vira um monolítico disfarçado.

## Decisão

O gateway gRPC é **thin** — sua responsabilidade se limita a:

### ✅ Responsabilidades do Gateway

| Responsabilidade | Como |
|-----------------|------|
| Autenticação | Valida tokens JWT (a implementar — atualmente local) |
| Autorização | Verifica permissões básicas |
| Roteamento | Cada RPC gRPC → adapter específico |
| Streaming | Proxy bidirecional para chat e voz |
| Observabilidade | Logs estruturados, métricas de latência |
| Tradução de protocolo | Protobuf ↔ DTOs internos |

### ❌ O Gateway NÃO faz

- Não acessa o banco de dados
- Não gerencia sessões de memória
- Não executa inferência de IA
- Não contém regras de negócio
- Não sabe o que é uma "memória" ou "automação" — só roteia

## Arquitetura

```
┌──────────────┐     gRPC      ┌──────────────────┐
│   Client     │ ────────────→ │  Thin Gateway    │
│  (MAUI/HUD)  │               │  (server.py)     │
└──────────────┘               └────────┬─────────┘
                                        │
                         ┌──────────────┼──────────────┐
                         │              │              │
                         ▼              ▼              ▼
                  ┌────────────┐ ┌────────────┐ ┌────────────┐
                  │ Cognition  │ │  Memory    │ │ Automation │
                  │ Adapter    │ │  Adapter   │ │  Adapter   │
                  └──────┬─────┘ └─────┬──────┘ └─────┬──────┘
                         │             │              │
                         ▼             ▼              ▼
                   ┌──────────┐ ┌────────────┐ ┌───────────┐
                   │ Kernel   │ │ Persisted  │ │ n8n/Event │
                   │/Brain    │ │ Memory     │ │ Bus       │
                   └──────────┘ └────────────┘ └───────────┘
```

## Implementação

O gateway consiste em:

- `app/grpc/server.py`: lifecycle do servidor (start/stop)
- `app/grpc/cognitive_service.py`: roteia Chat, Memory CRUD, Graph, Actions
- `app/grpc/voice_service.py`: roteia áudio bidirecional
- `app/grpc/automation_service.py`: roteia workflows, eventos, comandos

Nenhum desses arquivos importa `app.core.di`, `app.db.database`,
ou `app.models.models` — eles só conhecem **adapters**.

## Consequências

**Positivas:**
- Fácil de testar (gateway puro sem lógica de domínio)
- Substituível (pode trocar gRPC por outro protocolo sem afetar domínio)
- Escalável (cada adapter pode virar um serviço independente no futuro)

**Negativas:**
- Indireção adicional (um método a mais na chain de chamada)
- Adaptadores precisam ser mantidos em sincronia com o domínio

## Referências

- [ADR-0016](ADR-0016-domain-adapter-layer.md): Domain Adapter Layer
- `backend-core/app/grpc/server.py`
- `backend-core/app/adapters/`
