# Roadmap — Sexta-Feira OS (Arquitetura V2)

> **Missão:** Construir um Sistema Operacional Cognitivo Pessoal com interface HUD futurista.

---

## ✅ FASE 0 — Fundação (Completa)

- [x] Auditoria arquitetural completa do código existente
- [x] ADR-0001: Decisões arquiteturais da V2 (aprovado)
- [x] Documento de arquitetura V2 (ARCHITECTURE-v2.md)
- [x] Estrutura de pastas alvo criada
- [x] Definição de UI Engine components

---

## ✅ FASE ARC — Design System + shell nativo (Completa · 2026-07-31)

Substituiu o HUD da FASE 7 por uma identidade própria, documentada e
implementada. Ver `docs/design-system/`.

| Entrega | Estado |
|---|---|
| Design System (8 documentos, 16 entregáveis) | ✅ |
| Tokens em C# + XAML com paridade | ✅ |
| Reator SkiaSharp (bisel, 3 anéis de placas, bobinas, lentes, núcleo) | ✅ |
| Navegação radial de 2 níveis + setor anular de hover | ✅ |
| Estados automáticos via `ArcBrain` (chip reflete, nunca comanda) | ✅ |
| Rajdhani + JetBrains Mono empacotadas (SIL OFL 1.1) | ✅ |
| Build Windows + Android com 0 erros / 0 avisos | ✅ |
| App abre e renderiza nativamente | ✅ |

**Resolvido:** o bloco de identidade agora é desenhado no canvas
(`DrawIdentity`), contornando o layout do MAUI — todo overlay ancorado ao
centro daquele Grid media zero e nunca aparecia.

---

## 🔄 FASE 1 — UI Engine + HUD Radial (superada pela FASE ARC)

> Marcos M1.1–M1.4 e M1.6 foram cumpridos pelo shell ARC, com identidade
> própria em vez do tema Neon Dark original. M1.5 (conexão com o backend)
> segue pendente: o `GrpcClient` compila e o canal existe, mas nunca foi
> exercitado contra um kernel rodando.

**Objetivo:** Criar os componentes reutilizáveis de HUD e demonstrar navegação radial funcional.

### ui-engine/ (Componentes base — C#/.NET MAUI)

| Componente | Status | Descrição |
|------------|--------|-----------|
| `HudNode.cs` | 📋 | Classe base para todo elemento HUD |
| `CoreCircle.cs` | 📋 | Círculo central pulsante com glow |
| `RadialMenu.cs` | 📋 | Container que distribui itens em órbita |
| `RadialMenuItem.cs` | 📋 | Item clicável do menu radial |
| `OrbitalItem.cs` | 📋 | Item com órbita contínua (status) |
| `GlowCircle.cs` | 📋 | Efeito de brilho ao redor de círculos |
| `ParticleEmitter.cs` | 📋 | Sistema de partículas |
| `AnimationController.cs` | 📋 | Controle centralizado de animações |
| `TransitionController.cs` | 📋 | Transições entre camadas |
| `NavigationController.cs` | 📋 | Navegação baseada em árvore |
| `ThemeController.cs` | 📋 | Gerenciamento de temas |

### apps/maui/ (.NET MAUI)

| Módulo | Status | Descrição |
|--------|--------|-----------|
| `CognitiveHUD.csproj` | 📋 | Projeto MAUI inicial |
| `MainPage.xaml` | 📋 | HUD Shell com CoreCircle |
| `RadialMenuPage.xaml` | 📋 | Menu radial com 7 módulos |
| `Services/ApiClient.cs` | 📋 | Cliente HTTP para backend Python |
| `ViewModels/CoreHudViewModel.cs` | 📋 | ViewModel do HUD central |
| `ViewModels/RadialMenuViewModel.cs` | 📋 | ViewModel do menu radial |

### Marcos da FASE 1

- [ ] **M1.1:** CoreCircle renderizado com pulso e glow
- [ ] **M1.2:** RadialMenu com 7 itens orbitais (IA, Memória, Agenda, Biblioteca, Automações, Dispositivos, Configurações)
- [ ] **M1.3:** Clique no núcleo → expande menu radial (animado)
- [ ] **M1.4:** Clique em item → animação de seleção + glow
- [ ] **M1.5:** Conexão com backend Python (GET /health)
- [ ] **M1.6:** Tema Neon Dark aplicado globalmente

---

## 📋 FASE 2 — Navegação em Camadas

**Objetivo:** Implementar navegação profunda por árvore com transições animadas.

- [ ] NavigationController com árvore de 3 níveis
- [ ] Transição entre camadas (fade + escala + expansão radial)
- [ ] ParticleEmitter em transições
- [ ] Back navigation (recolhimento animado)
- [ ] Sub-módulos: Memória > Pessoas, Conversas, Arquivos, Conhecimento
- [ ] Conectar chat via REST (POST /api/v1/chat)
- [ ] Conectar memória via REST (POST /api/v1/memory/recall)
- [ ] Substituir SettingsScreen por HUD radial de configurações

---

## 📋 FASE 3 — Contratos Formais + Performance

**Objetivo:** Definir contratos gRPC/Protobuf entre frontend e backend.

- [ ] Protobuf definitions em `shared/protobuf/`
- [ ] Gateway gRPC no backend Python
- [ ] Stubs C# gerados
- [ ] Streaming de chat via gRPC
- [ ] Streaming de áudio bidirecional (futuro)
- [ ] Otimizações de performance de animação

---

## 📋 FASE 4 — Maturação e Expansão

**Objetivo:** Temas, desktop, plugins e percepção.

- [ ] ThemeController com temas customizáveis
- [ ] Modo Windows Desktop
- [ ] Plugin system (extensões de HUD)
- [ ] Integração com Rust (Perception Layer)
- [ ] Testes de animação (SkiaSharp unit tests)
- [ ] CI/CD para .NET MAUI (Android + Windows)

---

## 📋 FASE 5 (Longo Prazo)

- [ ] Presença ambiente (óculos, carro, relógio)
- [ ] Percepção de baixa latência (Rust integrado)
- [ ] Fine-tuning periódico automatizado
- [ ] Ecossistema de plugins aberto

---

## Legenda

| Símbolo | Significado |
|---------|-------------|
| ✅ | Completo |
| 🔄 | Em andamento |
| 📋 | Planejado |
| ⏸️ | Pausado / adiado |

---

## Débitos conhecidos

| # | Débito | Onde | Impacto |
|---|---|---|---|
| ~~D1~~ | ~~Bloco de identidade não renderiza~~ — **resolvido**: desenhado no canvas | `ReactorRenderer.DrawIdentity` | — |
| D2 | Itens orbitais podem sair da janela em alturas pequenas | `ArcGeometry.Orbit` | O raio de órbita é fixo em `2.40 R` e não considera a altura útil. |
| D3 | As 15 HUD Pages ainda usam a paleta antiga (`#0A0A12`) | `Pages/*.xaml` | Inconsistência com os tokens ARC (`Void #000308`). ~155 literais. |
| D4 | `GrpcClient` nunca exercitado contra um kernel real | `Services/GrpcClient.cs` | A seção de voz assume "primeiro transcript = STT, resto = resposta". Convenção não validada. |
| D5 | Rajdhani registrada mas não usada | `Arc.Typography.xaml` | Os quatro arquivos compartilham a família interna "Rajdhani"; o relógio caiu para JetBrains Mono. |
| D6 | Voz implementada mas **não verificada ponta a ponta** | `Services/ArcVoiceLoop.cs` | Compila e está ligada ao reator, mas captura de microfone e síntese nunca foram exercitadas com áudio real. |

