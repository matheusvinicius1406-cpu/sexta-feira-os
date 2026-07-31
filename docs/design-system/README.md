# ARC — Design System V1

> **A**utonomous **R**eactor **C**ore — a linguagem visual do J.A.R.V.I.S. / Sexta-Feira OS.

Este não é um dashboard. É um **núcleo inteligente**. Toda a interface orbita o reator central,
que nunca desaparece e nunca fica completamente parado.

---

## Índice

| # | Documento | Conteúdo |
|---|---|---|
| 00 | **README.md** *(este)* | Filosofia, identidade, guia visual, entregáveis |
| 01 | [TOKENS.md](01-TOKENS.md) | Cores, espaçamento, grid, raio, glow, movimento, geometria do reator |
| 02 | [TIPOGRAFIA.md](02-TIPOGRAFIA.md) | Famílias, escala, tracking, uso por papel |
| 03 | [COMPONENTES.md](03-COMPONENTES.md) | Catálogo completo — 24 componentes |
| 04 | [NAVEGACAO.md](04-NAVEGACAO.md) | Fluxo radial, wireframes, mapa de módulos |
| 05 | [MOVIMENTO.md](05-MOVIMENTO.md) | Estados de animação e microinterações |
| 06 | [MAUI.md](06-MAUI.md) | Guia de implementação, estrutura de pastas, nomenclatura |
| 07 | [CHECKLISTS.md](07-CHECKLISTS.md) | Acessibilidade, performance, consistência visual |

**Mockup navegável de alta fidelidade:** publicado como Artifact — reator vivo, navegação radial
de 2 níveis, 8 estados de IA, boot, command palette e overlay de voz. Use-o como referência
canônica de comportamento; esta documentação é a referência canônica de valores.

---

## 1. Filosofia

Cinco regras que não se negociam. Qualquer tela que viole uma delas está fora do sistema.

1. **O reator é o centro de tudo.** Ele nunca desaparece, nunca é substituído, nunca sai do
   centro geométrico. Todo conteúdo aparece *ao redor* dele.
2. **Nada é instantâneo.** Toda transição tem easing. Nenhuma propriedade salta.
3. **Nada fica parado.** Em ocioso o movimento é quase imperceptível — mas existe.
4. **Tudo sob demanda.** A tela inicial mostra 5 coisas. O resto surge quando pedido.
5. **Menos cor, mais luz.** A hierarquia é construída com luminosidade e opacidade, não com matiz.

### O que o sistema não é

Sem sidebar. Sem drawer. Sem tabs. Sem cards estilo Windows/Android. Sem barra de navegação
inferior. Sem breadcrumb textual longo. Sem paleta multicolorida.

---

## 2. Identidade

**ARC** é derivado de reatores de arco elétrico e instrumentação aeronáutica — não de super-heróis.
A referência de comportamento é um **HUD de instrumento**: leituras precisas, densidade baixa,
tipografia de painel, e um núcleo luminoso que comunica estado por intensidade.

O que dá identidade própria ao ARC, e o separa de qualquer HUD genérico:

| Assinatura | Descrição |
|---|---|
| **Setor anular** | Hover não é um retângulo nem um círculo — é uma **fatia de rosca** (annular sector) preenchida em azul translúcido com stroke de 1px. É o gesto visual mais reconhecível do sistema. |
| **Núcleo contido** | O reator ocupa ~10,5% do menor eixo da tela. Ele é pequeno e denso, não gigante. A escala é o que separa elegância de exagero. |
| **Relógio no núcleo** | A hora vive dentro do anel principal. É o único número grande da interface. |
| **Camadas contra-rotativas** | Cada anel gira em velocidade e direção próprias. Nunca dois anéis na mesma velocidade. |
| **Espaço negativo dominante** | ~70% da tela é vazio absoluto. Isso é design, não falta de conteúdo. |

---

## 3. Guia visual

### 3.1 Anatomia do reator

Todas as distâncias são múltiplos de **R**. Isso torna o sistema resolução-independente.

O reator é uma **montagem mecânica**: bisel de metal escovado, três anéis de placas biseladas
com luz escapando pelas frestas, oito bobinas radiais e uma garganta de lentes convergindo para
um centro branco-quente.

```
                         ┌─ 3.24 R ── boundary HUD (tracejado)
                   ┌───── 3.05 R ── wedge externo
             ┌───── 2.40 R ── órbita dos módulos
       ┌───── 1.78 R ── wedge interno
     ┌───── 1.70 R ── arco de status
    ┌───── 1.66 R ── anel de ticks (72 marcas)
   ┌───── 1.62 R ── anel segmentado HUD
  ╔══════ 1.58 R ─┐
  ║  BISEL METAL  │ 1.38–1.58 R · metal escovado, −1.6°/s
  ╠══════ 1.36 R ─┤
  ║   PLACAS A    │ 1.12–1.36 R · 12 placas, gap 4.5°, +4.2°/s
  ╠══════ 1.06 R ─┤
  ║   PLACAS B    │ 0.84–1.06 R · 8 placas, gap 6°, −6.8°/s
  ╠══════ 0.78 R ─┤   ╲ bobinas: 8 struts 0.52–1.34 R, −2.4°/s
  ║   PLACAS C    │ 0.60–0.78 R · 16 placas, gap 5°, +10.5°/s
  ╠══════ 0.56 R ─┤
  ║  LENTES (7)   │ 0.56 → 0.12 R · convergentes, aditivas
  ╠══════ 0.26 R ─┤
  ║  NÚCLEO ●     │ 0–0.26 R · branco-quente + bloom + flare
  ╚═══════════════┘
```

`R = clamp(min(largura, altura) × 0.105, 52, 104)`

**Nada de texto dentro do núcleo.** O centro é a região mais luminosa da tela — qualquer glifo
ali seria ilegível. A identidade vive logo **abaixo** do reator, em bloco:

```
        [ REATOR ]
      J.A.R.V.I.S.        ← 2.02 R · wordmark cromado
         21:47            ← 2.62 R · relógio, display 200
  GOOD EVENING, MATHEUS   ← rótulo 9px
```

O wordmark usa a rampa cromada de 7 paradas ([01-TOKENS §5.4](01-TOKENS.md#54-rampa-cromada--wordmark))
com uma passagem de brilho tingida pelo estado atual — ele respira junto com o reator.
Todo o bloco atenua para 30% quando a órbita abre, mas nunca desaparece.

### 3.2 Paleta

Neutros deslocados em direção ao azul do acento — escolhidos, não herdados.

| Papel | Token | Hex | Uso |
|---|---|---|---|
| Fundo absoluto | `Void` | `#000308` | Base de toda tela |
| Fundo de painel | `Abyss` | `#060A12` | Painéis flutuantes |
| Superfície | `Graphite` | `#0E1520` | Glass base |
| Superfície elevada | `Slate` | `#16202E` | Glass elevado |
| Metal inativo | `Steel` | `#2A3A4E` | Anéis inativos, ticks |
| **Acento primário** | `Arc` | `#2E7DFF` | Wedge, ícones, conectores |
| Acento profundo | `ArcDeep` | `#0B47B8` | Gradientes, sombra de glow |
| **Acento claro** | `Plasma` | `#35D6FF` | Foco, hover, cursor, pulso |
| Ignição | `Ignition` | `#C9F4FF` | Núcleo quente, texto máximo |
| Sucesso | `Vital` | `#2EE6A8` | Confirmação |
| Atenção | `Caution` | `#FFB23D` | Aviso |
| Falha | `Breach` | `#FF4D6A` | Erro |

**Regra de cor semântica:** `Vital` / `Caution` / `Breach` são *estado*, nunca decoração, e nunca
contam como acento. Fora de um estado ativo, elas não aparecem na tela.

### 3.3 Densidade

| Nível | Ocupação de tela | Quando |
|---|---|---|
| **Depth 0** — Core | ~8% | Ocioso. Reator, hora, data, operador, status. Só. |
| **Depth 1** — Módulos | ~26% | 12 módulos em órbita. |
| **Depth 2** — Submódulo | ~26% | 4–6 filhos do módulo ativo. |

Nenhum nível ultrapassa 30% de ocupação. Se um conteúdo não cabe, ele vira painel flutuante
ancorado ao reator — não uma página.

---

## 4. Entregáveis — mapa

| # | Entregável | Onde |
|---|---|---|
| 1 | Design System completo | Este diretório |
| 2 | Guia visual | §3 deste documento |
| 3 | Paleta de cores | §3.2 + [01-TOKENS](01-TOKENS.md#1-cor) |
| 4 | Tipografia | [02-TIPOGRAFIA](02-TIPOGRAFIA.md) |
| 5 | Componentes | [03-COMPONENTES](03-COMPONENTES.md) |
| 6 | Wireframes | [04-NAVEGACAO §2](04-NAVEGACAO.md#2-wireframes) |
| 7 | Mockups alta fidelidade | Artifact interativo |
| 8 | Fluxo de navegação radial | [04-NAVEGACAO §1](04-NAVEGACAO.md#1-fluxo) |
| 9 | Estados de animação | [05-MOVIMENTO §2](05-MOVIMENTO.md#2-estados) |
| 10 | Microinterações | [05-MOVIMENTO §3](05-MOVIMENTO.md#3-microinterações) |
| 11 | Guia de implementação MAUI | [06-MAUI](06-MAUI.md) |
| 12 | Estrutura de pastas | [06-MAUI §3](06-MAUI.md#3-estrutura-de-pastas) |
| 13 | Convenções de nomenclatura | [06-MAUI §4](06-MAUI.md#4-nomenclatura) |
| 14 | Checklist de acessibilidade | [07-CHECKLISTS §1](07-CHECKLISTS.md#1-acessibilidade) |
| 15 | Checklist de performance | [07-CHECKLISTS §2](07-CHECKLISTS.md#2-performance) |
| 16 | Checklist de consistência | [07-CHECKLISTS §3](07-CHECKLISTS.md#3-consistência-visual) |

---

## 5. Código

| Artefato | Caminho |
|---|---|
| Tokens C# | `ui-engine/Design/ArcTokens.cs` |
| Geometria do reator | `ui-engine/Design/ArcGeometry.cs` |
| Curvas de movimento | `ui-engine/Design/ArcMotion.cs` |
| Estados da IA | `ui-engine/Reactor/ReactorState.cs` |
| Renderer SkiaSharp | `ui-engine/Reactor/ReactorRenderer.cs` |
| Tokens XAML | `apps/maui/CognitiveHUD/Resources/Styles/Arc.Colors.xaml` |
| Estilos XAML | `apps/maui/CognitiveHUD/Resources/Styles/Arc.Styles.xaml` |
