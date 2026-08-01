# Arquitetura V2 — Sexta-Feira OS

> **Personal Cognitive Operating System**
>
> O Sexta-Feira NÃO é um chatbot, um app de IA, um launcher ou um assistente virtual.
> É um **Sistema Operacional Cognitivo Pessoal** — um cérebro privado com uma interface
> HUD futurista que o dono controla por círculos concêntricos.

---

## 1. Filosofia Central

```
┌─────────────────────────────────────────────┐
│     SEXTA-FEIRA = PCOS, não aplicativo       │
│                                              │
│  • Tudo gira em torno do NÚCLEO (cérebro)    │
│  • Não existem "telas" — existem camadas     │
│  • A navegação é radial, não linear          │
│  • Cada módulo é um HUD, não uma página      │
│  • Animações conduzem a experiência          │
└─────────────────────────────────────────────┘
```

### Princípios inegociáveis

| Princípio | Descrição |
|-----------|-----------|
| **Núcleo único** | Toda interface orbita o círculo central do cérebro |
| **Sem páginas** | Navegação por camadas radiais, não por telas |
| **Vivo** | Toda transição tem animação — nada é instantâneo |
| **HUD, não UI** | Visual holográfico/neon, não botões comuns |
| **Só meu** | Privacidade total. Local-first. Sem nuvem. |
| **Um cérebro, muitos corpos** | Celular, desktop, wearables — mesma mente |

---

## 2. Arquitetura em Camadas

```
┌──────────────────────────────────────────────────────────────┐
│                         APPS LAYER                            │
│  .NET MAUI (Android / Windows / macOS)                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  HUD Shell  │  RadialNav  │  Views  │  ViewModels   │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                       UI ENGINE                               │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐    │
│  │  Base   │ │ Controls │ │Animation │ │ Navigation     │    │
│  │ Compos. │ │ (Radial) │ │(Easing)  │ │ (Tree-based)   │    │
│  └────────┘ └──────────┘ └──────────┘ └────────────────┘    │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                     GATEWAY LAYER                             │
│  FastAPI + gRPC (opcional)  │  Contratos  │  Protobufs       │
│  Autenticação │  WebSocket  │  Streaming                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                   COGNITIVE BACKEND                           │
│  Python / FastAPI                                             │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────────────┐    │
│  │ Cognition│ │ Memory   │ │ Voice  │ │ Automations    │    │
│  │ (Ollama) │ │ (Neural) │ │(STT/TTS)│ │ (Teia)         │    │
│  └──────────┘ └──────────┘ └────────┘ └────────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────────────┐    │
│  │ Planning │ │ Decision │ │Learning│ │ Connectors     │    │
│  │ Engine   │ │ Engine   │ │ Engine │ │ (API registry)  │    │
│  └──────────┘ └──────────┘ └────────┘ └────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. UI ENGINE (Módulo Central)

### 3.1 Componentes Base

```
HudNode
├── Propriedades: Position, Rotation, Scale, Opacity, Glow
├── Estado: Idle, Hovered, Active, Expanding, Collapsing
└── Métodos: AnimateTo(), Pulse(), Glow(), FadeIn/FadeOut()

CoreCircle
├── O círculo central — o "cérebro"
├── Pulso suave contínuo
├── Ao clicar: expande para RadialMenu
└── Glow animado (cores dinâmicas por estado)

RadialMenu
├── Container que posiciona N filhos em órbita
├── Distribuição angular uniforme (360°/N)
├── Animação de entrada: expansão radial a partir do centro
└── Animação de saída: recolhimento ao centro

RadialMenuItem
├── Círculo com ícone + texto + glow
├── Tamanho: ~80dp
├── Estados: idle, hovered (expande), active (glow forte)
└── Ao clicar: ou abre subcamada ou executa ação

OrbitalItem
├── Similar ao RadialMenuItem, mas com órbita contínua
└── Usado para status/monitoramento (não para navegação)

GlowCircle
├── Desenha um gradiente radial ao redor de um HudNode
├── Cores animáveis (transições suaves)
└── Intensidade controlada por estado
```

### 3.2 Sistema de Animação

```
AnimationController
├── Timeline baseada em tempo (não frames)
├── Easing functions: Elastic, Bounce, CubicBezier, Circular
├── Animações encadeáveis (sequência)
└── Cancelamento seguro (não deixa estado inconsistente)

Transições Disponíveis:
├── ExpandRadial    → itens emergem do centro em arco
├── CollapseRadial  → itens recolhem ao centro
├── FadeTransition  → crossfade entre camadas
├── GlowPulse       → brilho pulsante contínuo
├── Orbit           → rotação orbital suave
├── ScaleBounce     → escala com efeito bouncing
└── ParticleBurst   → partículas na transição
```

### 3.3 Navegação por Árvore

```
NavigationController
├── Árvore hierárquica de módulos
├── Estado atual: caminho (ex: Core > Memória > Conhecimento)
├── Histórico de navegação (back suave)
└── Transição entre camadas

Árvore de navegação:

Nível 0: Core (núcleo central)
├── Nível 1:
│   ├── IA            → abre chat/agentes
│   ├── Memória       → abre sub-módulos de memória
│   ├── Agenda        → calendário/lembretes
│   ├── Biblioteca    → base de conhecimento
│   ├── Automações    → automações (Teia)
│   ├── Dispositivos  → corpos pareados
│   └── Configurações → ajustes do sistema
│
│   Nível 2 (ex: Memória):
│   ├── Pessoas
│   ├── Conversas
│   ├── Arquivos
│   └── Conhecimento
│       │
│       └── Nível 3 (ex: Conhecimento):
│           ├── PDFs
│           ├── Artigos
│           ├── Links
│           ├── Notas
│           ├── RAG
│           ├── Tags
│           └── Biblioteca
```

### 3.4 Temas

```
ThemeController
├── Tema padrão: "Neon Dark"
│   ├── Background: #0A0A0F (preto profundo)
│   ├── Primary: #00E5FF (ciano neon)
│   ├── Secondary: #7C4DFF (roxo)
│   ├── Accent: #FF6D00 (laranja)
│   └── Glow: gradiente radial do primary com alpha
│
├── Tema alternativo: "Holographic Light"
│   ├── Background: #F5F0FF (branco azulado)
│   ├── Primary: #6200EA (roxo escuro)
│   └── ...
│
└── Todos os temas implementam interface ITheme
```

---

## 4. BACKEND COGNITIVO (Python)

O backend atual (`backend-core/`) será movido para `backend/cognitive-core/`
sem alterações na lógica. A comunicação com o frontend MAUI será via:

| Protocolo | Uso | Status |
|-----------|-----|--------|
| REST (FastAPI) | Chat, CRUD, ações | ✅ Atual |
| WebSocket | Streaming, eventos ao vivo | ✅ Parcial |
| gRPC (futuro) | Contratos formais, alta performance | 📋 FASE 3 |

### Módulos do Backend

```
cognitive-core/
├── app/
│   ├── api/routers/    → 15+ endpoints (chat, memória, voz, etc.)
│   ├── brain/          → LocalBrain (Ollama), Memory, Cognition
│   ├── voice/          → STT (faster-whisper), TTS (Piper)
│   ├── automation/     → motor Teia
│   ├── action/         → Protocolo de Ação (dispositivos)
│   ├── connectors/     → API registry + Vault (Fernet)
│   ├── planning/       → Planning Engine
│   ├── decision/       → Decision Engine
│   ├── learning/       → Learning Engine
│   └── events/         → Event Bus
├── alembic/            → Migrações
└── tests/              → pytest (CI verde)
```

---

## 5. COMUNICAÇÃO FRONTEND ↔ BACKEND

```
.NET MAUI                          Python (FastAPI)
─────────                          ────────────────
CognitiveHUD                       cognitive-core
    │                                    │
    ├── gRPC (futuro) ──────────────────►│
    │   - Chat (streaming)               │
    │   - Voice (áudio bidirecional)      │
    │   - Eventos ao vivo                │
    │                                    │
    ├── REST ───────────────────────────►│
    │   - CRUD de memórias               │
    │   - Autenticação                   │
    │   - Ações/dispositivos             │
    │                                    │
    └── WebSocket ◄──────────────────────┤
        - Streaming de resposta (chat)    │
        - Comandos para dispositivos      │
        - Status updates                  │
```

### Contratos (shared/)

```
shared/
├── contracts/         → Interfaces/contratos em C#
│   ├── ICognitiveCore.cs
│   ├── IMemoryService.cs
│   ├── IVoiceService.cs
│   └── IAutomationService.cs
├── protobuf/          → Protobuf definitions (futuro)
│   ├── cognitive.proto
│   ├── memory.proto
│   └── voice.proto
└── schemas/           → Schemas compartilhados
    ├── models.py
    └── constants.py
```

---

## 6. ESTRUTURA DO REPOSITÓRIO (Nova)

```
sexta-feira-os/
├── apps/                          → Aplicações (interface)
│   └── maui/                      → .NET MAUI (CognitiveHUD)
│       ├── CognitiveHUD/          → App principal
│       │   ├── Views/             → HUD Shell, RadialNav, etc.
│       │   ├── ViewModels/        → MVVM ViewModels
│       │   ├── Services/          → API Client, Audio, etc.
│       │   └── Platforms/         → Android, Windows, etc.
│       └── CognitiveHUD.sln
│
├── backend/                       → Backend (cognição)
│   └── cognitive-core/            → Python FastAPI (movido de backend-core/)
│
├── ui-engine/                     → UI Engine (independente de plataforma)
│   ├── Base/                      → HudNode, CoreCircle, GlowCircle
│   ├── Controls/                  → RadialMenu, RadialMenuItem, OrbitalItem
│   ├── Animation/                 → AnimationController, TransitionController
│   ├── Navigation/                → NavigationController, NavigationTree
│   └── Themes/                    → ThemeController, ITheme, NeonDarkTheme
│
├── shared/                        → Compartilhado
│   ├── contracts/                 → Interfaces C#
│   ├── protobuf/                  → .proto definitions (futuro)
│   └── schemas/                   → Schemas Python
│
├── src/                           → Rust (camada de percepção, experimental)
│
├── plugins/                       → Plugins extensíveis (futuro)
├── docs/                          → Documentação
│   └── adr/                       → Architecture Decision Records
│
├── mcp-factory/                   → MCP Server (AI Factory)
├── orchestrator/                  → AI Orchestrator (CrewAI)
├── scripts/                       → Utilitários
└── tests/                         → Testes integrados
```

---

## 7. MAPA DE MIGRAÇÃO

### FASE 1 (Atual) — UI Engine + HUD Radial
**Objetivo:** Criar os componentes base de HUD e demonstrar navegação radial funcional.

- [ ] Criar `ui-engine/` com componentes base (C#, independente de plataforma)
- [ ] Criar `apps/maui/` com projeto .NET MAUI inicial
- [ ] Implementar `CoreCircle` com pulso e glow
- [ ] Implementar `RadialMenu` + `RadialMenuItem`
- [ ] Implementar `NavigationController` (árvore de navegação)
- [ ] Implementar `AnimationController` (transições radiais)
- [ ] Demonstrar: CoreCircle → clique → expande radial com 7 módulos
- [ ] Manter backend Python funcionando sem alterações

### FASE 2 — Navegação em Camadas
- [ ] Implementar navegação profunda (Nível 2 e 3 da árvore)
- [ ] Implementar transições entre camadas (fade + escala + expansão)
- [ ] Implementar `ParticleEmitter` para efeitos visuais
- [ ] Conectar ao backend: pelo menos chat e memória via REST
- [ ] Substituir tela de configurações por HUD radial

### FASE 3 — Contratos Formais + Performance
- [ ] Definir protobufs em `shared/protobuf/`
- [ ] Implementar gateway gRPC opcional no backend
- [ ] Implementar stubs C# a partir dos protos
- [ ] Adicionar streaming de áudio bidirecional

### FASE 4 — Maturação
- [ ] Temas customizáveis (ThemeController)
- [ ] Modo desktop (Windows)
- [ ] Plugin system
- [ ] Integração com Rust (percepção)

---

## 8. DECISÕES ARQUITETURAIS (Links)

| ADR | Título | Status |
|-----|--------|--------|
| ADR-0001 | Arquitetura V2 — Sexta-Feira OS como PCOS | ✅ Aprovado |

---

## 9. GLOSSÁRIO

| Termo | Definição |
|-------|-----------|
| **PCOS** | Personal Cognitive Operating System — Sistema Operacional Cognitivo Pessoal |
| **Núcleo/Core** | Círculo central que representa o cérebro do Sexta-Feira |
| **HUD** | Heads-Up Display — interface holográfica/neon |
| **Camada** | Nível da árvore de navegação (equivalente a "tela" em apps comuns) |
| **Módulo** | Cada nó da árvore (IA, Memória, Agenda, etc.) |
| **Corpo** | Dispositivo que se conecta ao cérebro (celular, desktop, etc.) |
| **UI Engine** | Motor de interface responsável por renderizar HUDs, animações e navegação |
