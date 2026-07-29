# ADR-0001: Arquitetura V2 — Sexta-Feira OS como Sistema Operacional Cognitivo Pessoal

- **Data:** 2026-07-29
- **Status:** Aprovado
- **Decisor:** Matheus Vinicius (Dono) + Claude Code (Arquiteto Principal)
- **Tipo:** Arquitetura Fundamental

## Contexto

O Sexta-Feira OS foi originalmente construído como um kernel cognitivo local (Python/FastAPI)
com um cliente Android nativo (Kotlin/Compose). Após análise aprofundada da visão do projeto
e do código existente, decidiu-se por uma reorientação arquitetural profunda para transformar
o projeto em um **Sistema Operacional Cognitivo Pessoal (Personal Cognitive Operating System — PCOS)**,
não um aplicativo convencional.

## Decisões

### Decisão 1: .NET MAUI como plataforma de frontend única

**Opção escolhida:** .NET MAUI puro
**Opções consideradas:** Android nativo (Kotlin/Compose), Híbrido (Compose + MAUI)

**Justificativa:**
- .NET MAUI permite C# cross-platform (Android, Windows, macOS, iOS) com um único codebase
- C# tem suporte nativo a animações complexas via `Microsoft.Maui.Graphics` e `SkiaSharp`
- MVVM nativo do .NET MAUI alinha-se perfeitamente com a arquitetura limpa
- Windows Desktop torna-se viável como plataforma-alvo (o cérebro roda no desktop)
- Elimina a fragmentação de ter que manter Android + Web + Desktop em stacks diferentes
- A performance do .NET MAUI para HUDs é adequada (o foco é UI-HUD, não jogos AAA)

**Consequências:**
- Reescrita completa do frontend Android em C#/.NET MAUI
- O código Kotlin/Compose existente servirá como referência de implementação
- A interface web (jarvis-ui/) será absorvida pelo MAUI ou mantida como alternativa leve

### Decisão 2: UI Engine como camada de abstração visual

**Opção escolhida:** Criar módulo `ui-engine/` com componentes reutilizáveis
**Opções consideradas:** Manter lógica de HUD espalhada nas Views

**Justificativa:**
- Centraliza toda a lógica de renderização de HUD (círculos, arcos, partículas, animações)
- Permite tema consistente (neon, holográfico, escuro)
- Componentes reutilizáveis reduzem duplicação e aumentam consistência
- A UI Engine é independente do MAUI — poderia ser portada para qualquer plataforma

**Hierarquia de componentes:**

```
HudNode          → nó base do HUD (posição, rotação, escala, opacidade)
RadialMenu       → container que posiciona filhos em órbita
RadialMenuItem   → item clicável com ícone, texto, glow
CoreCircle       → círculo central (o "cérebro")
OrbitalItem      → item que orbita o núcleo com movimento suave
GlowCircle       → efeito de brilho ao redor de círculos
ParticleEmitter  → sistema de partículas
AnimationController  → transições, easing, timelines
TransitionController → fade, escala, expansão radial, recolhimento
NavigationController → árvore de navegação radial em camadas
```

### Decisão 3: Navegação radial em camadas (não por páginas/telas)

**Opção escolhida:** Árvore de navegação centrada no núcleo
**Opções consideradas:** Drawer, BottomNav, TabBar, NavHost tradicional

**Justificativa:**
- Substitui completamente o conceito de "telas" ou "páginas"
- Cada nível da árvore substitui o anterior com animação radial
- O usuário nunca sente que "navegou para outra tela" — apenas mudou o nível do núcleo
- Alinha-se com a identidade de "Sistema Operacional Cognitivo"

**Árvore de navegação:**

```
Core
├── IA
├── Memória
│   ├── Pessoas
│   ├── Conversas
│   ├── Arquivos
│   └── Conhecimento
│       ├── PDFs
│       ├── Artigos
│       ├── Links
│       ├── Notas
│       ├── RAG
│       ├── Tags
│       └── Biblioteca
├── Agenda
├── Biblioteca
├── Automações
├── Dispositivos
└── Configurações
```

### Decisão 4: Manter Python como backend cognitivo (sem reescrita)

**Opção escolhida:** Manter Python/FastAPI + evoluir
**Opções consideradas:** Re-escrever backend em Rust, Go ou C#

**Justificativa:**
- O backend Python já está maduro: 15+ routers, memória-grafo, tool-calling, voz local, automações, CI verde
- Python tem o melhor ecossistema de IA/LLM (Ollama, embeddings, RAG, STT/TTS)
- Rewrite seria antieconômico e arriscado — o backend não tem problemas arquiteturais graves
- A comunicação via contratos (REST hoje, gRPC futuramente) desacopla frontend do backend

**Consequências:**
- Mover `backend-core/` → `backend/cognitive-core/` para alinhar com nova estrutura
- Adicionar gateway gRPC opcional (camada extra, não substituição)
- Manter REST como protocolo primário por simplicidade

### Decisão 5: Rust experimental mantido como camada futura

**Opção escolhida:** Manter `src/` experimental, não integrar agora
**Opções consideradas:** Integrar via PyO3 imediatamente, transformar em daemon separado

**Justificativa:**
- O foco atual é UI Engine + Navegação Radial (FASE 1)
- A camada de percepção Rust será valiosa quando os corpos ambientes existirem
- Integrar agora criaria dependência sem caso de uso imediato

### Decisão 6: Contratos formais (gRPC/Protobuf) são futuros

**Opção escolhida:** Adiar para FASE 3, manter REST + schemas Pydantic por enquanto
**Opções consideradas:** Implementar gRPC imediatamente

**Justificativa:**
- O acoplamento atual via REST é suficiente para o desenvolvimento inicial
- Definir protobufs antes de ter a UI Engine funcionando seria premature optimization
- Os schemas Pydantic do FastAPI já servem como contratos

## Diagrama Arquitetural

```
┌─────────────────────────────────────────────────────────┐
│                    APPS (Interface)                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              .NET MAUI (CognitiveHUD)              │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────────┐   │   │
│  │  │ CoreHUD │ │RadialNav │ │ Views/Controls   │   │   │
│  │  └─────────┘ └──────────┘ └──────────────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
│                        │                                 │
│              ┌─────────▼──────────┐                      │
│              │    UI Engine        │                      │
│              │ (Components/HUD)    │                      │
│              └─────────┬──────────┘                      │
└────────────────────────┼─────────────────────────────────┘
                         │ gRPC / REST
┌────────────────────────┼─────────────────────────────────┐
│              ┌─────────▼──────────┐                      │
│              │   Gateway API      │                      │
│              │ (FastAPI + gRPC)   │                      │
│              └─────────┬──────────┘                      │
│                        │                                 │
│   ┌────────────────────┼────────────────────┐            │
│   │                    │                    │            │
│   ▼                    ▼                    ▼            │
│ ┌────────┐      ┌───────────┐       ┌──────────┐       │
│ │Cognição│      │  Memória   │       │  Voz     │       │
│ │(Ollama)│      │  (SQLite)  │       │(STT/TTS) │       │
│ └────────┘      └───────────┘       └──────────┘       │
│                    BACKEND COGNITIVO (Python)            │
└─────────────────────────────────────────────────────────┘
```

## Referências

- Visão do projeto: `VISION.md`
- Arquitetura atual: `docs/ARCHITECTURE.md`
- Prompt de rearquitetura do dono (2026-07-29)
- AGENTS.md (contrato de agentes)
