# 01 — Tokens

Toda decisão visual do ARC é um token. Nenhum valor literal em código de tela.

Fonte da verdade: `ui-engine/Design/ArcTokens.cs` (C#) e
`apps/maui/CognitiveHUD/Resources/Styles/Arc.Colors.xaml` (XAML). Os dois **devem** ser mantidos
em sincronia — o C# serve o canvas SkiaSharp, o XAML serve os controles MAUI.

---

## 1. Cor

### 1.1 Ground — neutros

Deslocados em direção ao azul do acento. Um cinza puro leria como não-escolhido.

| Token | Hex | RGB | Uso |
|---|---|---|---|
| `Void` | `#000308` | 0, 3, 8 | Fundo da aplicação. Nunca use `#000000` puro. |
| `Abyss` | `#060A12` | 6, 10, 18 | Fundo de painel flutuante opaco |
| `Graphite` | `#0E1520` | 14, 21, 32 | Base de glass |
| `Slate` | `#16202E` | 22, 32, 46 | Glass elevado, hover de superfície |
| `Steel` | `#2A3A4E` | 42, 58, 78 | Anéis inativos, ticks, divisores fortes |

### 1.2 Acento

| Token | Hex | Uso |
|---|---|---|
| `Arc` | `#2E7DFF` | Acento primário. Wedge, ícones, conectores, gradientes |
| `ArcDeep` | `#0B47B8` | Fim de gradiente, sombra colorida |
| `Plasma` | `#35D6FF` | Foco, hover, cursor, pulso de voz, indicador ativo |
| `Ignition` | `#C9F4FF` | Núcleo quente, texto de intensidade máxima |

### 1.3 Semântica

Estado, nunca decoração. Não conta como acento.

| Token | Hex | Significado |
|---|---|---|
| `Vital` | `#2EE6A8` | Sucesso, online, saudável |
| `Caution` | `#FFB23D` | Aviso, degradado, atenção |
| `Breach` | `#FF4D6A` | Erro, falha, offline crítico |

### 1.4 Tinta (texto)

Hierarquia por opacidade sobre `Void`, não por matiz.

Contraste medido sobre `Void` (`#000308`) pela fórmula WCAG 2.1 de luminância relativa.

| Token | Valor | Contraste vs `Void` | WCAG | Uso |
|---|---|---|---|---|
| `InkHi` | `rgba(233,244,255,0.94)` | **16.27:1** | AAA | Títulos, valores primários |
| `Ink` | `rgba(200,219,240,0.72)` | **7.61:1** | AAA | Corpo, leituras |
| `InkLo` | `rgba(160,184,212,0.66)` | **4.73:1** | AA | Rótulos, legendas, texto de apoio |
| `InkGhost` | `rgba(140,168,200,0.20)` | **1.32:1** | ✗ | **Somente decorativo — nunca texto** |

> ⚠️ **`InkLo` foi calibrado, não escolhido a olho.** O valor original de `0.42` de alpha
> produzia 2.48:1 — reprovação em AA inclusive para texto grande. `0.66` é o menor alpha que
> ultrapassa 4.5:1 mantendo a leitura "apagada" que o HUD pede.
>
> `InkGhost` (1.32:1) é reservado a elementos puramente não-textuais: pips inativos, linhas de
> grade, conectores. Qualquer glifo que carregue informação usa no mínimo `InkLo`.

### 1.4.1 Contraste dos acentos

| Token | Contraste vs `Void` | Texto? |
|---|---|---|
| `Ignition` | 17.58:1 | ✅ AAA |
| `Vital` | 12.79:1 | ✅ AAA |
| `Plasma` | 12.02:1 | ✅ AAA |
| `Caution` | 11.50:1 | ✅ AAA |
| `Breach` | 6.42:1 | ✅ AA |
| `Arc` | 5.40:1 | ✅ AA |
| `Steel` | 1.78:1 | ❌ estrutural apenas (anéis, ticks) |

`Steel` nunca recebe texto. É a cor do metal inativo.

### 1.5 Glass

| Token | Valor | Uso |
|---|---|---|
| `Glass` | `rgba(14,21,32,0.55)` + blur 14px | Chips, strip de comando |
| `GlassHi` | `rgba(28,42,62,0.62)` + blur 18px | Painéis HUD, diálogos |
| `Hairline` | `rgba(120,170,235,0.16)` | Borda padrão de glass |
| `HairlineHi` | `rgba(120,190,255,0.38)` | Borda de foco / ativo |

### 1.6 Glow

Glow no ARC é **aditivo**, sempre. Nunca `DropShadow` opaco.

| Nível | Blur | Alpha | Uso |
|---|---|---|---|
| `Glow.Subtle` | 8px | 0.35 | Dots de status, pips ativos |
| `Glow.Focus` | 16px | 0.60 | Ícone em hover, foco de teclado |
| `Glow.Core` | 5.5 × raio | gradiente 0.85 → 0 | Bloom do núcleo |

---

## 2. Espaçamento

Escala base 4. Sem valores fora dela.

| Token | px | Uso típico |
|---|---|---|
| `S1` | 4 | Gap interno de ícone+texto |
| `S2` | 8 | Gap de linha, padding de chip |
| `S3` | 12 | Gap entre grupos relacionados |
| `S4` | 16 | Padding de painel compacto |
| `S5` | 24 | Padding de painel padrão |
| `S6` | 32 | Separação entre blocos |
| `S7` | 48 | Margem de canto (desktop) |
| `S8` | 64 | Respiro de seção |

### 2.1 Margens de canto (responsivo)

```
padding: clamp(20px, 3.4vh, 40px) clamp(22px, 3.4vw, 48px)
```

Escala com a viewport para que a telemetria nunca encoste na borda em ultrawide nem invada o
reator em mobile.

---

## 3. Grid

O ARC **não usa grid de colunas**. O sistema de layout é **polar**:

| Eixo | Unidade | Descrição |
|---|---|---|
| Radial | múltiplos de `R` | Distância do centro |
| Angular | `360° / n` | Distribuição uniforme, ângulo inicial `−90°` (12 horas) |

Grid cartesiano existe apenas nos **quatro cantos de telemetria** e dentro de **painéis HUD**,
onde é um flex/grid simples com `gap` da escala de espaçamento.

---

## 4. Raio

| Token | px | Uso |
|---|---|---|
| `RadiusSm` | 2 | Bordas de painel, inputs |
| `RadiusMd` | 4 | Diálogos, command palette |
| `RadiusLg` | 8 | Painéis HUD grandes |
| `RadiusPill` | 999 | Chips, strip, toasts |

Cantos do wedge anular são **naturalmente arredondados** pela geometria do arco — não aplique
raio adicional.

---

## 5. Geometria do reator

Múltiplos de `R`. Constantes em `ui-engine/Design/ArcGeometry.cs`.

### 5.1 Corpo do reator

| Camada | Múltiplo de R | Contagem | Gap | Rotação (°/s) |
|---|---|---|---|---|
| Núcleo quente | 0 → 0.26 | — | — | — |
| Lentes convergentes | 0.56 → 0.12 | 7 | — | íris +3.0 |
| **Placas C** | 0.60 → 0.78 | 16 | 5° | **+10.5** |
| **Placas B** | 0.84 → 1.06 | 8 | 6° | **−6.8** |
| Bobinas (struts) | 0.52 → 1.34 | 8 | — | **−2.4** |
| **Placas A** | 1.12 → 1.36 | 12 | 4.5° | **+4.2** |
| Bisel de metal | 1.38 → 1.58 | — | — | **−1.6** |

### 5.2 Instrumentação HUD

| Camada | Múltiplo de R | Traço | Rotação (°/s) |
|---|---|---|---|
| Anel segmentado (5) | 1.62 | 1.2px, gap 26° | +7.0 |
| Anel de ticks (72) | 1.66 | 1px, 6 longas | −3.5 |
| Arco de status | 1.70 | 2px, cap redondo | respirando 30°↔96° |
| Wedge interno | 1.78 | — | — |
| **Órbita dos módulos** | **2.40** | — | — |
| Wedge externo | 3.05 | — | — |
| Boundary | 3.24 | 1px tracejado 1/7 | −1.15 |

### 5.3 Varredura especular

O que faz o metal parecer metal não é o gradiente — é o **realce especular girando**.

| | |
|---|---|
| Velocidade | `+14.0 °/s`, escalada por `lerp(0.35, 1, glow)` |
| Independência | **Não** é multiplicada por `Spin`. O metal continua reluzindo mesmo em `offline`. |
| Implementação | Gradiente cônico com 14 paradas: dois realces (um forte em 0.115, um fraco em 0.675) |

**Rampa de metal.** Deslocada fortemente para o azul: este não é aço neutro, é aço encharcado
da luz do que ele contém. Um metal cinza aqui leria como maquete; o desvio cromático é o que faz
o conjunto parecer iluminado por dentro.

| Token | Hex | Papel |
|---|---|---|
| `MetalDeep` | `#050A16` | Fundo da fresta |
| `MetalShadow` | `#101E36` | Sombra da placa |
| `MetalMid` | `#2D4468` | Corpo |
| `MetalLight` | `#6E9AD0` | Face iluminada |
| `MetalSpec` | `#D6ECFF` | Realce especular |

### 5.4 Rampa cromada — wordmark

O wordmark **J.A.R.V.I.S.** usa um gradiente **vertical** de 7 paradas, não radial.

| Parada | Hex | Papel |
|---|---|---|
| 0.00 | `#F2FAFF` | Topo, luz direta |
| 0.20 | `#BEDFF9` | Queda |
| 0.40 | `#639BD6` | Aproximação do horizonte |
| **0.50** | **`#143A66`** | **Horizonte especular** |
| 0.58 | `#3F7EC2` | Saída do horizonte |
| 0.76 | `#96C6EC` | Luz refletida |
| 1.00 | `#E4F3FF` | Base, bounce light |

> A banda escura em 0.50 é o **horizonte especular** — a linha onde o metal deixa de refletir o
> céu e passa a refletir o chão. É o que separa metal polido de um simples gradiente azul.
> Remova-a e o efeito colapsa inteiro, por mais bem escolhidas que sejam as outras paradas.

O gradiente é ancorado à **altura de maiúscula e à linha de base**, não ao canvas — assim o
horizonte cruza o meio das letras em qualquer tamanho:

```csharp
SKShader.CreateLinearGradient(
    new SKPoint(0, baseline - size * 0.78f),
    new SKPoint(0, baseline + size * 0.22f),
    ArcTokens.ChromeRamp, ArcTokens.ChromeStops, SKShaderTileMode.Clamp);
```

Uma passagem de brilho desfocada (`SKMaskFilter` sigma 9) é pintada **antes**, tingida por
`Tint` do estado atual — o wordmark respira junto com o reator em vez de flutuar sobre ele.

**Raio base:**
```
R_dp = clamp(min(largura_px, altura_px) / densidade × 0.105, 52, 104)
R_px = R_dp × densidade
```

> Os limites 52 e 104 são **dp, não pixels**. Um teto de 104px parece certo
> num desktop 1x e desaba para ~38dp num celular 2,75x, encolhendo o HUD
> inteiro e tornando o relógio ilegível. O clamp precisa morder na unidade
> que a pessoa percebe.

**Regra de contra-rotação:** camadas adjacentes nunca giram na mesma direção nem na mesma
velocidade. Isso é o que produz a sensação de profundidade 3D sem 3D real.

---

## 6. Movimento

### 6.1 Curvas

| Token | cubic-bezier | Uso |
|---|---|---|
| `EaseHud` | `0.16, 1, 0.3, 1` | Padrão. Expansão, fade, deslocamento |
| `EaseSnap` | `0.34, 1.4, 0.44, 1` | Overshoot. Entrada de item orbital, diálogo |
| `EaseExit` | `0.7, 0, 0.84, 0` | Saída. Colapso, dismiss |

### 6.2 Durações

| Token | ms | Uso |
|---|---|---|
| `DurInstant` | 120 | Mudança de cor em hover |
| `DurFast` | 220 | Microinteração, chip |
| `DurBase` | 340 | Transição de estado padrão |
| `DurSlow` | 550 | Expansão radial completa |
| `DurBoot` | 2200 | Sequência de boot |

### 6.3 Taxas de aproximação (loop contínuo)

Propriedades contínuas do reator não usam duração — usam **aproximação exponencial**,
independente de frame-rate:

```csharp
value += (target - value) * (1 - MathF.Exp(-rate * deltaSeconds));
```

| Propriedade | `rate` |
|---|---|
| `Glow` | 3.2 |
| `Spin` | 2.6 |
| `CoreScale` | 4.0 |
| `Tint` (por canal) | 3.0 |
| `Open` (expansão orbital) | 5.5 |
| `Hover` | 8.0 |
| `WedgeAngle` | 11.0 |
| `Proximity` | 6.0 |

> Por que exponencial e não `Animation`: o reator nunca "chega" a um destino — ele persegue um
> alvo que muda. Uma animação com duração precisaria ser cancelada e recriada a cada mudança de
> estado, produzindo saltos. A aproximação exponencial absorve mudanças de alvo sem descontinuidade.

---

## 7. Elevação

Sem sombra projetada. Elevação no ARC é comunicada por **blur de fundo + opacidade de borda**.

| Nível | Blur | Fundo | Borda |
|---|---|---|---|
| 0 — canvas | — | `Void` | — |
| 1 — chip | 14px | `Glass` | `Hairline` |
| 2 — painel | 18px | `GlassHi` | `Hairline` |
| 3 — diálogo | 20px | `GlassHi` + gradiente | `HairlineHi` |
| 4 — overlay | 20px | `rgba(0,3,8,0.72)` | — |
