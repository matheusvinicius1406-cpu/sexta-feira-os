# 06 — Implementação em .NET MAUI

Stack: **.NET 8 · MAUI · C# · MVVM (CommunityToolkit.Mvvm) · SkiaSharp · Lottie**.

---

## 1. Divisão de responsabilidades

A regra que evita 90% dos problemas: **o reator é pintado, o HUD é composto.**

| Camada | Tecnologia | Por quê |
|---|---|---|
| Reator, órbita, wedge, partículas | `SKCanvasView` (SkiaSharp) | Centenas de arcos e gradientes por frame. Nenhum sistema de layout sobrevive a isso. |
| Rótulos, telemetria, chips, painéis | Controles MAUI sobre o canvas | Texto de 8–11px precisa do rasterizador de fonte nativo. Texto em canvas fica borrado. |
| Overlays (palette, diálogo, toast) | MAUI em `Grid` sobreposto | Precisam de foco, teclado e acessibilidade reais. |
| Animação de marca / boot opcional | Lottie | Só se houver arte vetorial pronta. O boot atual não precisa. |

**Não desenhe texto pequeno no `SKCanvas`.** A composição de rótulos como elementos MAUI
posicionados por `TranslationX/Y` a partir das coordenadas polares calculadas no renderer é o
padrão do sistema.

### 1.1 Por que SkiaSharp e não `GraphicsView`

`Microsoft.Maui.Graphics` (usado hoje em `ui-engine/`) não expõe:

- gradiente cônico → sem varredura especular, sem metal
- `BlendMode.Plus` confiável em todas as plataformas → sem bloom aditivo
- `SKPath` com sub-caminhos para clip em lote → sem otimização de placas

`SkiaSharp` já está no `.csproj`. A migração das primitivas do reator para `SKCanvas` é
obrigatória; o `RadialMenu` existente pode ser reaproveitado quase inteiro, pois é lógica de
layout, não de pintura.

---

## 2. Anatomia da tela

```xml
<Grid BackgroundColor="{StaticResource Arc.Color.Void}">

    <!-- 0 · reator + órbita + wedge, 60 fps -->
    <skia:SKCanvasView x:Name="ReactorSurface"
                       EnableTouchEvents="True"
                       PaintSurface="OnPaintSurface"
                       Touch="OnTouch" />

    <!-- 1 · rótulos orbitais, posicionados pelo renderer -->
    <AbsoluteLayout x:Name="OrbitLabels" InputTransparent="True" />

    <!-- 2 · telemetria de canto + relógio -->
    <controls:ArcTelemetryLayer InputTransparent="True" />

    <!-- 3 · painéis HUD ancorados -->
    <controls:ArcPanelHost x:Name="Panels" />

    <!-- 4 · overlays -->
    <controls:ArcCommandPalette x:Name="Palette" IsVisible="False" />
    <controls:ArcToastHost x:Name="Toasts" />

</Grid>
```

### 2.1 Loop de render

`SKCanvasView` não tem loop próprio. Dirija-o com um timer no dispatcher:

```csharp
public sealed partial class ReactorHost : ContentView
{
    readonly IDispatcherTimer _timer;
    readonly Stopwatch _clock = Stopwatch.StartNew();
    TimeSpan _last;

    public ReactorHost()
    {
        _timer = Dispatcher.CreateTimer();
        _timer.Interval = TimeSpan.FromMilliseconds(16);   // ~60 fps
        _timer.Tick += (_, _) =>
        {
            var now = _clock.Elapsed;
            var dt  = (float)(now - _last).TotalSeconds;
            _last = now;

            // Nunca confie no intervalo do timer: ele desliza sob carga.
            _renderer.Update(MathF.Min(dt, 0.05f));
            ReactorSurface.InvalidateSurface();
        };
    }

    protected override void OnHandlerChanged()
    {
        base.OnHandlerChanged();
        if (Handler is null) _timer.Stop(); else _timer.Start();
    }
}
```

> **Pare o timer quando a página sai de vista.** Um reator girando em background drena bateria
> em Android sem nenhum benefício. `OnDisappearing` → `_timer.Stop()`.

---

## 3. Estrutura de pastas

```
ui-engine/                              SextaFeira.UIEngine
├── Design/
│   ├── ArcTokens.cs                    cores, espaçamento, raio, tipografia
│   ├── ArcGeometry.cs                  múltiplos de R, contagens, gaps, rotações
│   └── ArcMotion.cs                    easings, durações, Approach()
├── Reactor/
│   ├── ReactorState.cs                 enum + tabela de alvos
│   ├── ReactorModel.cs                 propriedades contínuas + Update(dt)
│   ├── ReactorRenderer.cs              orquestra as camadas
│   └── Layers/
│       ├── MetalBandLayer.cs           bisel
│       ├── PlateRingLayer.cs           placas A / B / C
│       ├── StrutLayer.cs               bobinas + pulsos
│       ├── LensLayer.cs                garganta convergente
│       ├── HotCoreLayer.cs             núcleo + bloom + flare
│       ├── ParticleLayer.cs
│       └── HudRingLayer.cs             ticks, segmentos, arco de status
├── Navigation/
│   ├── RadialMenu.cs                   ← existente, mantido
│   ├── RadialMenuItem.cs               ← existente, mantido
│   ├── SectorHighlight.cs              wedge anular
│   └── NavigationController.cs         ← existente, mantido
└── Controls/                           primitivas compartilhadas

apps/maui/CognitiveHUD/                 SextaFeira.CognitiveHUD
├── Resources/
│   ├── Fonts/                          Rajdhani-*.ttf, JetBrainsMono-*.ttf
│   └── Styles/
│       ├── Arc.Colors.xaml
│       ├── Arc.Typography.xaml
│       └── Arc.Styles.xaml
├── Controls/
│   ├── ReactorHost.xaml{.cs}
│   ├── ArcHudPanel.xaml{.cs}
│   ├── ArcStatusChip.xaml{.cs}
│   ├── ArcCommandPalette.xaml{.cs}
│   ├── ArcToastHost.xaml{.cs}
│   └── ArcWaveform.xaml{.cs}
├── ViewModels/
│   ├── ShellViewModel.cs               profundidade, módulo ativo, breadcrumb
│   ├── ReactorViewModel.cs             assina EventBus → ReactorState
│   └── <Feature>ViewModel.cs
├── Pages/                              ← 15 páginas da FASE 7, redesenhadas
└── Services/                           ← existentes
```

---

## 4. Nomenclatura

### 4.1 C#

| Elemento | Convenção | Exemplo |
|---|---|---|
| Primitiva do design system | prefixo `Arc` | `ArcTokens`, `ArcHudPanel`, `ArcStatusChip` |
| Camada do reator | sufixo `Layer` | `PlateRingLayer`, `HotCoreLayer` |
| ViewModel | sufixo `ViewModel` | `ReactorViewModel` |
| Serviço | `I` + sufixo `Service` | `IVoiceService` |
| Enum de estado | singular | `ReactorState.Listening` |
| Campo privado | `_camelCase` | `_animationProgress` |
| Constante de geometria | `PascalCase` em `ArcGeometry` | `ArcGeometry.OrbitRadius` |

**Não** prefixe com `Jarvis`, `SF` ou `Hud` — `Arc` é o único prefixo do design system.

### 4.2 Chaves XAML

Namespace por pontos, do geral ao específico:

```
Arc.Color.<Token>          Arc.Color.Plasma
Arc.Space.<N>              Arc.Space.4
Arc.Radius.<Size>          Arc.Radius.Pill
Arc.Text.<Role>            Arc.Text.Label
Arc.Style.<Control>        Arc.Style.GhostButton
```

Isso mantém o IntelliSense agrupado e torna óbvio quando alguém inventa um token fora do sistema.

### 4.3 Arquivos

| Tipo | Padrão |
|---|---|
| Controle | `Arc<Nome>.xaml` + `.xaml.cs` |
| Página | `<Feature>Page.xaml` |
| Dicionário | `Arc.<Categoria>.xaml` |
| Documento | `NN-ASSUNTO.md` |

---

## 5. Tokens em código

`ArcTokens.cs` é a fonte para o canvas. `Arc.Colors.xaml` é a fonte para os controles.
**Os dois devem casar.** O teste em `07-CHECKLISTS §3` verifica isso automaticamente.

```csharp
public static class ArcTokens
{
    // Ground
    public static readonly SKColor Void     = SKColor.Parse("#000308");
    public static readonly SKColor Graphite = SKColor.Parse("#0E1520");
    // Accent
    public static readonly SKColor Arc      = SKColor.Parse("#2E7DFF");
    public static readonly SKColor Plasma   = SKColor.Parse("#35D6FF");
    // ...
}
```

```xml
<Color x:Key="Arc.Color.Void">#000308</Color>
<Color x:Key="Arc.Color.Plasma">#35D6FF</Color>
```

---

## 6. Coordenadas polares → controles MAUI

O renderer calcula as posições; a camada de rótulos apenas as consome.

```csharp
// No renderer, por item:
float angle = (-90f + 360f / count * index) * ArcMotion.Deg2Rad;
float r     = ArcGeometry.OrbitRadius * R * easedOpen;
var  point  = new SKPoint(cx + MathF.Cos(angle) * r,
                          cy + MathF.Sin(angle) * r);
```

```csharp
// Na view — converta pixels de dispositivo para unidades independentes.
float scale = (float)DeviceDisplay.MainDisplayInfo.Density;
label.TranslationX = point.X / scale - label.Width  / 2;
label.TranslationY = point.Y / scale + iconSize * 1.5 / scale;
```

> `SKCanvasView.CanvasSize` vem em **pixels**; `TranslationX/Y` do MAUI está em **unidades
> independentes de densidade**. Esquecer a divisão por `Density` é o bug número um desta
> integração — em um telefone 3× tudo aparece três vezes mais longe do centro.

---

## 7. Estado vindo do backend

```csharp
public sealed partial class ReactorViewModel : ObservableObject
{
    [ObservableProperty] ReactorState state = ReactorState.Idle;

    public ReactorViewModel(IEventBus bus)
    {
        bus.Subscribe<WakeDetected>(_    => State = ReactorState.Listening);
        bus.Subscribe<UtteranceEnded>(_  => State = ReactorState.Thinking);
        bus.Subscribe<StreamStarted>(_   => State = ReactorState.Speaking);
        bus.Subscribe<StreamCompleted>(_ => State = ReactorState.Idle);
        bus.Subscribe<LinkLost>(_        => State = ReactorState.Offline);
        bus.Subscribe<LinkRestored>(_    => State = ReactorState.Idle);
    }
}
```

O `ReactorModel` observa `State` e apenas troca os **alvos**; o loop de render faz o resto.
Nenhum código de UI decide quando a IA está pensando. Ver
[05-MOVIMENTO §1](05-MOVIMENTO.md#1-princípio-o-estado-não-é-um-controle).

---

## 8. Especificidades de plataforma

| Assunto | Windows | Android |
|---|---|---|
| Blur de fundo | Mica/Acrylic via `Microsoft.UI.Composition` | Não existe nativo — use `SKImageFilter.CreateBlur` sobre um snapshot, ou um sólido a 92% |
| `SKCanvasView` | `SKGLView` para GPU | `SKCanvasView` (CPU) é suficiente; `SKGLView` aquece o aparelho |
| Fontes | `.ttf` em `Resources/Fonts` | idem |
| Barra de status | ocultar chrome da janela | `WindowCompat.setDecorFitsSystemWindows(false)` + barras transparentes |
| Splash | `MauiSplashScreen` com fundo `#000308` | idem — elimina o flash branco |

`backdrop-filter` não existe no MAUI. Onde o design pede glass e a plataforma não entrega blur,
**caia para um sólido de alta opacidade** (`Graphite` a 92%) em vez de tentar emular — vidro mal
emulado lê pior do que um sólido honesto.
