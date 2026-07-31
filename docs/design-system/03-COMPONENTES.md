# 03 — Componentes

24 componentes. Cada um tem anatomia, tokens, estados e mapeamento MAUI.

**Regra de composição:** nenhum componente duplica outro. Se dois precisam do mesmo visual,
extraia um terceiro. `ArcGlassSurface` é a base de tudo que tem fundo.

---

## Índice

**Superfície** — 1 · Glass Surface · 2 · HUD Panel · 3 · Card Holográfico · 4 · Floating Window
**Navegação** — 5 · Radial Menu · 6 · Circular Menu · 7 · Context Menu · 8 · Breadcrumb Rail
**Ação** — 9 · Botão · 10 · Input · 11 · Command Palette · 12 · Search Overlay
**Feedback** — 13 · Status Chip · 14 · Toast · 15 · Tooltip · 16 · Notification
**Voz** — 17 · Voice Overlay · 18 · Waveform · 19 · Voice Animation
**Sistema** — 20 · Dialog · 21 · Terminal · 22 · Boot Screen · 23 · Loading · 24 · AI Thinking

---

## Superfície

### 1 · `ArcGlassSurface`

A primitiva de fundo. Todo componente com superfície herda dela.

| Propriedade | Valor |
|---|---|
| Fundo | `Glass` (nível 1) ou `GlassHi` (nível 2+) |
| Blur | 14px / 18px / 20px por nível de elevação |
| Borda | 1px `Hairline`; `HairlineHi` quando focado |
| Raio | `RadiusSm` (2) padrão |
| Highlight interno | `inset 0 1px 0 rgba(140,190,255,0.10)` — simula borda de vidro |

**Sem sombra projetada.** Elevação é blur + opacidade de borda. Ver [01-TOKENS §7](01-TOKENS.md#7-elevação).

---

### 2 · `ArcHudPanel`

Painel de conteúdo ancorado ao reator. **Substitui a página tradicional.**

```
┌─────────────────────────────────────┐
│ ▸ MEMORY · SEMANTIC          ✕      │  ← header 40px, Label 9px
├─────────────────────────────────────┤
│                                     │
│   conteúdo                          │  ← padding S5 (24)
│                                     │
├─────────────────────────────────────┤
│ 1 284 ENTRIES        LAST 04:21     │  ← footer de telemetria, Readout 11px
└─────────────────────────────────────┘
```

| | |
|---|---|
| Largura | `min(420px, 34vw)` |
| Posição | Ancorado a `3.4 R` do centro, no quadrante do módulo ativo |
| Entrada | `Open` 0→1 com `EaseSnap`, 340ms, translação de 16px na direção radial |
| Saída | `EaseExit`, 220ms |

**Nunca centralizado sobre o reator.** O painel orbita; o reator permanece visível.

---

### 3 · `ArcHoloCard`

Item de lista dentro de um painel. Não é um card estilo Material — é uma **faixa** com trilho
lateral que codifica estado.

```
┃ SEMANTIC INDEX                 4.2 MB
┃ 1 284 vetores · atualizado 04:21
▲
└─ trilho 2px: Arc (normal) · Vital/Caution/Breach (estado)
```

| Estado | Trilho | Fundo |
|---|---|---|
| Normal | `Arc` 40% | transparente |
| Hover | `Plasma` | `rgba(46,125,255,0.10)` |
| Ativo | `Plasma` + glow 8px | `rgba(46,125,255,0.16)` |
| Alerta | `Caution` / `Breach` | `rgba(cor, 0.08)` |

Sem `CornerRadius` nos quatro cantos — apenas o trilho define a borda esquerda.

---

### 4 · `ArcFloatingWindow`

Painel destacável e arrastável, para trabalho paralelo (terminal, browser).

Herda `ArcHudPanel` + barra de arraste + botões `minimizar` / `fechar`.
Máximo de **3 janelas** simultâneas — acima disso, a mais antiga colapsa em chip.

---

## Navegação

### 5 · `ArcRadialMenu`

**O componente central do sistema.** Distribui itens em órbita ao redor do reator.

| Propriedade | Valor |
|---|---|
| Raio de órbita | `2.40 R` |
| Ângulo inicial | `−90°` (12 horas) |
| Distribuição | `360° / n`, uniforme |
| Tamanho do ícone | `0.30 R`, ×1.22 em hover |
| Conector | Hairline de `1.50 R` até a borda do ícone, alpha 0.05 → 0.25 em hover |

**Entrada escalonada:** cada item `i` de `n` começa com atraso proporcional:

```csharp
float stagger = Math.Clamp((open - (i / (float)n) * 0.18f) / 0.82f, 0f, 1f);
float eased   = 1f - MathF.Pow(1f - stagger, 3f);   // cubic-out
```

O item viaja de `r = 0` até `r = 2.40 R`, com escala `0.55 → 1.0` e opacidade `0 → 1`.

---

### 6 · `ArcSectorHighlight` — o setor anular

**A assinatura visual do ARC.** É o que substitui hover retangular.

```
        ╱▔▔▔▔▔╲          rOut = 3.05 R
      ╱  ▓▓▓▓▓  ╲
     │  ▓▓ ◉ ▓▓  │       span = (360/n) × 0.86
      ╲  ▓▓▓▓▓  ╱
        ╲▁▁▁▁▁╱          rIn  = 1.72 R
```

| Camada | Valor |
|---|---|
| Preenchimento | Gradiente radial `Arc`: 0.06 (interno) → 0.17 (55%) → 0.12 (externo) |
| Traço | 1px `Arc` a 0.46 alpha |
| Span | `(360° / n) × 0.86` — a folga de 14% cria o gap entre setores |
| Movimento | O setor **desliza** entre posições em 11.0 de taxa, nunca salta |

**Caminho geométrico:**

```csharp
using var path = new SKPath();
path.AddArc(outerRect, a0Deg, sweepDeg);
path.ArcTo(innerRect, a0Deg + sweepDeg, -sweepDeg, false);
path.Close();
```

---

### 7 · `ArcContextMenu`

Menu radial curto (3–5 itens) invocado por pressão longa / botão direito, ancorado **no ponto do
gesto**, não no reator. Raio de órbita fixo em `72px`. Span de 180°, orientado para o lado com
mais espaço livre.

---

### 8 · `ArcBreadcrumbRail`

Indicador de profundidade no topo. Três pips + rótulo.

```
  ●  ○  ○     CORE
  ●  ●  ○     CORE · MODULES
  ●  ●  ●     CORE · MEMORY
```

Pip ativo: `Plasma` 5px com glow 9px. Inativo: `InkGhost` 4px.
Rótulo: `Label` 9px, `InkLo`.

---

## Ação

### 9 · `ArcButton`

| Variante | Fundo | Borda | Texto |
|---|---|---|---|
| **Ghost** (padrão) | transparente | nenhuma | `InkLo` → `InkHi` em hover |
| **Outline** | transparente | 1px `Hairline` | `Ink` |
| **Solid** | `Plasma` | nenhuma | `Void` |
| **Danger** | transparente | 1px `Breach` 55% | `Breach` |

Todos: `RadiusPill`, padding `8px 13px`, `Label` 9px UPPER, transição `DurFast` com `EaseHud`.
Hover de Ghost adiciona `rgba(46,125,255,0.12)` de fundo.

---

### 10 · `ArcInput`

Sem caixa. Uma **linha inferior** de 1px que acende no foco.

```
NOME DO AGENTE
Atlas▏
────────────────────────────  ← Hairline → Plasma no foco, 220ms
```

| Estado | Linha | Rótulo |
|---|---|---|
| Repouso | `Hairline` | `InkLo` |
| Foco | `Plasma` + glow 8px | `Plasma` |
| Erro | `Breach` | `Breach` + mensagem abaixo |
| Desabilitado | `InkGhost` tracejado | `InkGhost` |

---

### 11 · `ArcCommandPalette`

Overlay central. `Ctrl/Cmd + K` ou `/`.

```
┌──────────────────────────────────────────┐
│ ▸  COMANDO, MÓDULO OU CONSULTA           │  ← input, Body 12px
├──────────────────────────────────────────┤
│┃ MEMORY                          MODULE  │  ← selecionado: trilho Plasma
│  MEMORY · SEMANTIC               ACTION  │
│  AGENTS · SPAWN                  ACTION  │
└──────────────────────────────────────────┘
```

Fundo do overlay: `rgba(0,3,8,0.72)` + blur 20px. Caixa: 560px máx, `RadiusMd`,
glow externo `0 0 80px rgba(46,125,255,0.16)`.
Entrada: `translateY(10px) scale(0.98)` → normal, `EaseSnap` 400ms.

---

### 12 · `ArcSearchOverlay`

Variante do Command Palette para busca de conteúdo (arquivos, memória). Mesma caixa, mas
resultados agrupados por fonte com contagem, e preview à direita em telas ≥ 1024px.

---

## Feedback

### 13 · `ArcStatusChip`

```
( ● ) STANDBY
```

Pill de glass com dot pulsante. O dot respira em 3.2s (`opacity 0.45 ↔ 1`).

| Estado | Borda | Texto | Dot |
|---|---|---|---|
| `idle` | `Hairline` | `Ink` | `Plasma` |
| `listening` | `Plasma` 50% | `Plasma` | `Plasma` |
| `thinking` | `Arc` 50% | `Ink` | `Plasma` |
| `error` | `Breach` 55% | `Breach` | `Breach` |
| `offline` | `Hairline` 10% | `InkLo` | `InkLo`, sem glow, sem pulso |

---

### 14 · `ArcToast`

Pill efêmera acima do rodapé. Dot + texto. 2600ms, entrada `translateY(8px)` + fade,
`EaseHud` 450ms. Máximo **um** por vez — um novo substitui o anterior.

---

### 15 · `ArcTooltip`

`Label` 9px em `ArcGlassSurface` nível 1, `RadiusSm`. Aparece após **600ms** de hover,
desaparece em 120ms. Offset de 10px na direção oposta ao centro do reator.

---

### 16 · `ArcNotification`

Empilha no canto superior direito, abaixo da telemetria. Herda `ArcHoloCard` com trilho
semântico. Máximo 4 visíveis; excedente vira contador `+3`.
Auto-dismiss só para `Vital`. `Caution` e `Breach` exigem dispensa manual.

---

## Voz

### 17 · `ArcVoiceOverlay`

Waveform + legenda, ancorado a `14vh` do rodapé. Não escurece a tela — o reator continua visível
e pulsando. Entrada `translateY(20px)` + fade, 500ms.

### 18 · `ArcWaveform`

34 barras de 2px, `RadiusSm`, `Plasma` com glow 8px.

```csharp
// Duas senoides em frequências incomensuráveis evitam padrão perceptível
float v = 3f + MathF.Abs(
    MathF.Sin(t * 6.5f + i * 0.42f) *
    MathF.Sin(t * 2.1f + i * 0.13f)) * 26f * amplitude;
```

| Estado | Amplitude |
|---|---|
| `listening` | 1.00 |
| `speaking` | 0.72 |
| outros | 0 (barras em 3px, opacidade 0.15) |

### 19 · `ArcVoiceAnimation` (núcleo)

Não é um componente separado — é o reator reagindo. Ver [05-MOVIMENTO §2](05-MOVIMENTO.md#2-estados).

---

## Sistema

### 20 · `ArcDialog`

`ArcGlassSurface` nível 3 sobre overlay nível 4. Largura `min(480px, 88vw)`.
Ações alinhadas à direita, ação primária em `Solid`. `Esc` fecha. Foco preso dentro do diálogo.

### 21 · `ArcTerminal`

`ArcFloatingWindow` com `ArcData` 12px, entrelinha 1.5. Prompt `▸` em `Plasma`.
Fundo `Abyss` (opaco — legibilidade vence o vidro aqui). Scrollback 2000 linhas.

### 22 · `ArcBootScreen`

```
              A R C
     ────────────────────────  ← barra 190×1px, preenche em Plasma
          REACTOR ONLINE       ← Label 9px, InkGhost
```

Sete passos × 260ms + 420ms de repouso ≈ 2.2s. Ao fim, fade de 900ms revela o reator já em
rotação — nunca partindo do zero.

Passos: `INITIALIZING` → `REACTOR ONLINE` → `MOUNTING MEMORY` → `LINKING AGENTS` →
`CALIBRATING VOICE` → `HANDSHAKE OK` → `ARC READY`.

**Splash** = primeiro frame do boot (marca + fundo `Void`), usado como splash nativo da
plataforma para eliminar o flash branco.

### 23 · `ArcLoading`

Sem spinner. O **arco de status** do reator (`1.14 R`) alonga e encurta entre 30° e 96°.
Carregamento localizado dentro de um painel usa a mesma forma em escala reduzida.

### 24 · `ArcThinkingScreen`

Não é uma tela — é o estado `thinking`: anéis a **3.6×** a velocidade base, tint desloca para
`Arc`, núcleo encolhe 6%, `Core Load` sobe para 62–92%. A interface permanece navegável.
