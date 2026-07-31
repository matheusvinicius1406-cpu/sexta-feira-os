# 02 — Tipografia

A voz do ARC é de **leitura de instrumento**, não de aplicativo. Rótulos são curtos, em caixa
alta, com tracking largo. O único número grande da interface é o relógio no núcleo.

---

## 1. Famílias

Duas famílias, dois papéis. Nenhuma terceira.

### 1.1 Display — `Rajdhani`

Geométrica, condensada, com pesos leves que sustentam tracking largo sem virar caligrafia.
Desenhada para painéis e sinalização — é a razão de existir dela.

| | |
|---|---|
| **Licença** | SIL Open Font License 1.1 — redistribuição livre |
| **Pesos usados** | 300 Light, 400 Regular, 500 Medium |
| **Usos** | Relógio do núcleo, títulos de painel, marca de boot |
| **Alternativa** | `Chakra Petch` (mais técnica), `Saira` (mais neutra) |

### 1.2 Data — `JetBrains Mono`

Monoespaçada com altura-x generosa e dígitos inconfundíveis. É a voz de toda telemetria,
rótulo e leitura numérica.

| | |
|---|---|
| **Licença** | SIL Open Font License 1.1 |
| **Pesos usados** | 300 Light, 400 Regular, 500 Medium |
| **Usos** | Rótulos, telemetria, chips, breadcrumb, terminal, command palette |
| **Alternativa** | `IBM Plex Mono`, `Share Tech Mono` |

> **Por que mono como voz principal?** Porque o conteúdo é telemetria. Larguras fixas mantêm
> colunas de números alinhadas sem tabular-nums, e a textura mecânica é a do assunto. A display
> entra só onde o tamanho justifica personalidade.

### 1.3 Registro no MAUI

**Instalado.** Arquivos em `apps/maui/CognitiveHUD/Resources/Fonts/`, declarados como `MauiFont`
no `.csproj` (o SDK do MAUI faz glob automático de `*.xaml`, mas **não** de fontes) e registrados
em `MauiProgram.cs`:

```csharp
builder.ConfigureFonts(fonts =>
{
    fonts.AddFont("Rajdhani-Light.ttf",        "ArcDisplayLight");
    fonts.AddFont("Rajdhani-Regular.ttf",      "ArcDisplay");
    fonts.AddFont("Rajdhani-Medium.ttf",       "ArcDisplayMedium");
    fonts.AddFont("Rajdhani-Bold.ttf",         "ArcDisplayBold");   // wordmark
    fonts.AddFont("JetBrainsMono-Light.ttf",   "ArcDataLight");
    fonts.AddFont("JetBrainsMono-Regular.ttf", "ArcData");
    fonts.AddFont("JetBrainsMono-Medium.ttf",  "ArcDataMedium");
});
```

> **Sempre referencie o alias, nunca o nome do arquivo.** O arquivo é detalhe de implementação;
> trocar `Rajdhani` por `Chakra Petch` deve ser uma linha no `MauiProgram`, não uma varredura
> pelo projeto.

### 1.3.1 Licenciamento

Ambas as famílias são **SIL Open Font License 1.1**, que permite empacotar e redistribuir dentro
de uma aplicação. A licença exige que o texto acompanhe as fontes: `OFL-Rajdhani.txt` e
`OFL-JetBrainsMono.txt` ficam em `Resources/Fonts/` e são incluídos no projeto como `None`
(não como `MauiFont` — não são fontes).

| Família | Autor | Licença |
|---|---|---|
| Rajdhani | Indian Type Foundry | OFL 1.1 |
| JetBrains Mono | The JetBrains Mono Project Authors | OFL 1.1 |

### 1.4 O wordmark é desenhado, não escrito

**J.A.R.V.I.S.** não pode ser um `Label`. Um `Label` do MAUI aceita apenas `TextColor` sólido, e
o wordmark depende de um gradiente vertical de 7 paradas com horizonte especular — sem ele, vira
texto azul.

Ele é pintado no `SKCanvas`, via `ReactorRenderer.DrawWordmark`:

```csharp
_text.Typeface = displayTypeface;
_text.TextSize = R * ArcGeometry.WordmarkSize;   // 0.42 R
_text.TextAlign = SKTextAlign.Center;
_text.Shader = SKShader.CreateLinearGradient(
    new SKPoint(0, baseline - size * 0.78f),
    new SKPoint(0, baseline + size * 0.22f),
    ArcTokens.ChromeRamp, ArcTokens.ChromeStops, SKShaderTileMode.Clamp);
```

Esta é a **única** exceção à regra "não desenhe texto no canvas". Ela se sustenta porque o
wordmark é grande (0.42 R ≈ 21–44px), é uma string fixa que nunca precisa de leitor de tela como
texto vivo, e precisa de um preenchimento que nenhum controle nativo produz.

Exponha o nome via `SemanticProperties.Description` em um elemento irmão invisível para que o
leitor de tela ainda o anuncie.

---

## 2. Escala

Escala restrita — sete degraus. Não invente tamanhos intermediários.

| Token | px | Família | Peso | Tracking | Caixa | Uso |
|---|---|---|---|---|---|---|
| `Wordmark` | `0.42 × R` | Display | **700** | `0.15em` | — | **J.A.R.V.I.S.** — preenchimento cromado, não cor sólida |
| `Clock` | `0.28 × R` | Display | 200 | `0.24em` | — | Relógio, abaixo do wordmark |
| `Title` | 22 | Display | 300 | `0.30em` | UPPER | Título de painel HUD |
| `Heading` | 15 | Display | 400 | `0.22em` | UPPER | Cabeçalho de seção |
| `Body` | 13 | Data | 400 | `0.06em` | — | Corpo, descrições |
| `Readout` | 11 | Data | 400 | `0.12em` | — | Telemetria, valores |
| `Label` | 9 | Data | 500 | `0.26em` | UPPER | Rótulos de campo, chips |
| `Micro` | 8 | Data | 500 | `0.24em` | UPPER | Rótulos orbitais |

### 2.1 Piso de tamanho

`Micro` (8px) é o **piso absoluto** e só é permitido com **três** condições simultâneas:

1. Caixa alta com tracking ≥ `0.20em`
2. Cor mínima `InkLo` (4.73:1)
3. Redundância não-textual — a informação também está codificada por posição, ícone ou forma

Rótulos orbitais atendem as três (posição angular + ícone). Nenhum outro texto do sistema usa 8px.

---

## 3. Tracking e text-indent

Tracking largo em caixa alta cria um problema mecânico: o último caractere carrega o espaçamento
extra, deslocando o texto para a esquerda do centro óptico.

**Regra:** todo texto com tracking recebe `text-indent` igual ao tracking.

```css
.label {
  letter-spacing: 0.26em;
  text-indent: 0.26em;   /* compensa o tracking do último glifo */
}
```

No MAUI, `Label` não expõe `letter-spacing`. Duas saídas:

| Situação | Solução |
|---|---|
| Texto estático curto | `CharacterSpacing` (MAUI 8+, em *device units*) |
| Texto em canvas | `SKPaint` com `TextSize` + desenho glifo a glifo |
| Fallback | Espaçar manualmente na string: `"C O R E"` — **só** para a marca de boot |

---

## 4. Entrelinha

| Contexto | Line height |
|---|---|
| `Title` / `Heading` | 1.15 |
| `Body` | 1.6 |
| `Readout` / `Label` / `Micro` | 1.0 (linha única) |

Corpo de texto nunca ultrapassa **65 caracteres** de largura. Em painéis HUD isso significa
largura máxima de ~48ch com `Body` a 13px.

---

## 5. Números

Toda coluna de dígitos usa **tabular figures**.

```css
font-variant-numeric: tabular-nums;
```

```xml
<!-- MAUI: JetBrains Mono já é monoespaçada — tabular por construção -->
<Label FontFamily="ArcData" Text="{Binding Latency, StringFormat='{0:000} MS'}" />
```

**Padding de zero à esquerda é obrigatório** em telemetria, para que o valor não mude de largura
e "pule" a cada atualização: `007 MS`, não `7 MS`.

---

## 6. Escrita

O texto da interface é design, não decoração.

| Regra | ✗ | ✅ |
|---|---|---|
| Nomeie pelo que a pessoa reconhece | `gRPC Channel State` | `Link` |
| Voz ativa no controle | `Ativação de voz` | `Ouvir` |
| Confirmação espelha o comando | `Ouvir` → `Operação concluída` | `Ouvir` → `Ouvindo` |
| Erro diz o que houve e o que fazer | `Erro 0x8007` | `Link perdido — reconectando em 3 s` |
| Sem desculpas, sem vaguidão | `Desculpe, algo deu errado` | `Modelo indisponível — tente outro` |

Saudação usa o nome do operador e a hora real: `Good evening, Matheus`. Nunca genérico.
