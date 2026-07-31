# 07 — Checklists

Três portões antes de qualquer merge que toque a UI.

---

## 1. Acessibilidade

### 1.1 Contraste

- [ ] Todo texto informativo usa `InkLo` (4.73:1) ou mais claro
- [ ] `InkGhost` (1.32:1) aparece **apenas** em elementos não-textuais
- [ ] `Steel` (1.78:1) nunca recebe texto — é cor estrutural
- [ ] Estado nunca é comunicado **só** por cor: sempre acompanha texto, ícone ou posição
- [ ] Contraste recalculado sempre que um token de tinta mudar (ver script em §3.3)

### 1.2 Tamanho de texto

- [ ] Corpo ≥ 13px, telemetria ≥ 11px
- [ ] 8px (`Micro`) restrito a rótulos orbitais, que satisfazem as três condições de
      [02-TIPOGRAFIA §2.1](02-TIPOGRAFIA.md#21-piso-de-tamanho)
- [ ] Layout sobrevive a 200% de escala de fonte do sistema sem sobreposição

> **Limitação reconhecida:** 8–9px é pequeno. É aceitável aqui porque cada rótulo é redundante
> com um ícone e uma posição angular fixa, e nenhuma tarefa depende de lê-lo. Se um rótulo virar
> a única fonte de uma informação, ele sobe para `Readout` (11px).

### 1.3 Teclado

- [ ] `Tab` percorre os itens orbitais em ordem angular horária
- [ ] `← →` movem o setor anular entre itens adjacentes
- [ ] `Enter` ativa; `Esc` sobe um nível
- [ ] **O setor anular é o indicador de foco** — mouse e teclado compartilham a mesma forma
- [ ] Nenhuma armadilha de foco fora de diálogos; dentro deles, foco preso e devolvido ao fechar
- [ ] `Ctrl/Cmd + K` abre a Command Palette de qualquer profundidade

### 1.4 Leitor de tela

- [ ] `SemanticProperties.Description` em todo item orbital: `"Memory, módulo 2 de 12"`
- [ ] Mudança de profundidade anuncia o novo contexto via `SemanticScreenReader.Announce`
- [ ] Mudança de estado da IA é anunciada: `"Ouvindo"`, `"Processando"`, `"Respondendo"`
- [ ] O `SKCanvasView` é `IsInAccessibleTree="False"` — ele é decorativo; a informação vive nos
      rótulos MAUI sobrepostos
- [ ] Toasts usam região `Polite`; erros usam `Assertive`

### 1.5 Movimento

- [ ] `prefers-reduced-motion` / *Reduzir movimento* do SO desliga rotação, partículas e varredura
- [ ] Com movimento reduzido, estado continua legível por cor, texto e opacidade
- [ ] Nenhum flash acima de 3 Hz em qualquer estado, incluindo `Error`

### 1.6 Alvos de toque

- [ ] Alvo mínimo 44×44 dp — o ícone orbital tem `0.30 R` (≈31px em R=104), então o **hit test é
      o setor anular inteiro**, não o ícone
- [ ] Reator inteiro (até `1.58 R`) é a área de toque do "voltar"

---

## 2. Performance

### 2.1 Orçamento de frame — 16.6ms

- [ ] Reator + órbita + partículas em **< 8ms** por frame em hardware alvo
- [ ] Medido com `SKCanvasView` real, não em debug com breakpoints

### 2.2 Regras de desenho

- [ ] **Um clip por anel de placas**, não um por placa — todas as placas de um anel compartilham
      um único `SKPath` com sub-caminhos
- [ ] **Um gradiente cônico por anel**, criado fora do laço de placas
- [ ] `SKPaint` reutilizado entre frames — alocar `SKPaint` em `OnPaintSurface` é a causa
      número um de GC stutter
- [ ] `SKPath` de ícones construído uma vez, escalado pela matriz do canvas
- [ ] `dpr` limitado a 2 — acima disso o custo quadruplica sem ganho visível

```csharp
// Errado — aloca 36 objetos por frame
foreach (var plate in plates) using var paint = new SKPaint { ... };

// Certo — campos reutilizados, apenas propriedades mudam
_platePaint.Shader = _metalShader;
canvas.DrawPath(_allPlates, _platePaint);
```

### 2.3 Contagens

| Recurso | Teto |
|---|---|
| Partículas | `clamp(W×H / 28000, 26, 84)` |
| Placas totais | 36 (16 + 8 + 12) |
| Bobinas | 8 |
| Gradientes cônicos por frame | 4 |
| Itens orbitais | 12 (nível 1), 6 (nível 2) |
| Painéis flutuantes | 3 |

### 2.4 Ciclo de vida

- [ ] Timer de render **parado** em `OnDisappearing` e quando o handler é destruído
- [ ] Timer parado quando o app vai para background (Android `OnPause`)
- [ ] `dt` limitado a 0.05s — sem isso, voltar do background dá um salto de rotação
- [ ] Nenhuma alocação em `Update(dt)`

### 2.5 Memória

- [ ] Sem vazamento de handler de evento no `EventBus` — `Unsubscribe` em `Dispose`
- [ ] Bitmaps de fonte não recriados por frame
- [ ] Teste: 10 min em `Idle` com alocação estável

---

## 3. Consistência visual

### 3.1 Tokens

- [ ] **Zero literais de cor** fora de `ArcTokens.cs` e `Arc.Colors.xaml`
- [ ] **Zero valores de espaçamento** fora da escala base-4
- [ ] Nenhuma distância do reator em pixels — só múltiplos de `R`
- [ ] Nenhuma duração fora de `ArcMotion`

```bash
# Literais de cor fugindo do sistema
rg -n '#[0-9A-Fa-f]{6}' --glob '!**/Arc.Colors.xaml' --glob '!**/ArcTokens.cs' \
   apps/maui ui-engine
```

### 3.2 Regras estruturais

- [ ] O reator está no centro geométrico em **toda** viewport testada
- [ ] Nenhuma profundidade ultrapassa 30% de ocupação de tela
- [ ] Nenhum painel cobre o reator
- [ ] Nenhuma sidebar, drawer, tab bar ou seta de "voltar" foi introduzida
- [ ] Máximo 2 níveis orbitais; o terceiro é painel
- [ ] Cores semânticas (`Vital`/`Caution`/`Breach`) só aparecem em estado ativo

### 3.3 Paridade C# ↔ XAML

Teste automatizado que impede os dois conjuntos de tokens de divergirem:

```csharp
[Fact]
public void XamlColorsMatchArcTokens()
{
    var xaml = LoadResourceDictionary("Arc.Colors.xaml");
    foreach (var (name, expected) in ArcTokens.AllColors)
    {
        var actual = xaml[$"Arc.Color.{name}"];
        Assert.Equal(expected.ToString(), actual.ToString());
    }
}
```

- [ ] Teste passa
- [ ] Todo token novo entra nos **dois** arquivos no mesmo commit

### 3.4 Contraste automatizado

```csharp
[Theory]
[InlineData(nameof(ArcTokens.InkLo),  4.5)]   // AA texto normal
[InlineData(nameof(ArcTokens.Ink),    4.5)]
[InlineData(nameof(ArcTokens.InkHi),  7.0)]   // AAA
public void InkTokensMeetContrast(string token, double minimum)
    => Assert.True(Contrast(ArcTokens.Get(token), ArcTokens.Void) >= minimum);
```

### 3.5 Revisão visual

- [ ] Comparado lado a lado com o mockup de referência em Depth 0, 1 e 2
- [ ] Testado em: 1920×1080, 1366×768, 2560×1080 (ultrawide), 412×915 (mobile), dobrável aberto
- [ ] Testado em `Idle`, `Listening`, `Thinking`, `Speaking`, `Warning`, `Error`, `Offline`
- [ ] Capturas anexadas ao PR para os estados alterados
