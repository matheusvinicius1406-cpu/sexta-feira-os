# 05 — Movimento e estados

---

## 1. Princípio: o estado não é um controle

**Nenhum estado da IA é acionado manualmente.** Não existe botão de "modo escuta", nem seletor de
"modo pensando". O estado é uma **consequência observável** do que o sistema está fazendo.

```
sinal real  ──►  ReactorState  ──►  alvos contínuos  ──►  render
```

| Sinal de entrada | Origem real | Estado resultante |
|---|---|---|
| Wake word / tecla de voz | `IVoiceService.WakeDetected` | `Listening` |
| Fim de captura de áudio | `IVoiceService.UtteranceEnded` | `Thinking` |
| Primeiro token do modelo | `ICognitionEngine.StreamStarted` | `Speaking` |
| Fim da resposta | `ICognitionEngine.Completed` | `Idle` |
| Job em background | `EventBus` → `TaskStarted` | `Thinking` (sem voz) |
| Latência > limiar | `HealthMonitor` | `Warning` |
| Canal gRPC caiu | `GrpcClient.StateChanged` | `Offline` → `Error` |
| Sem interação > 10 min | `IdleWatcher` | `Sleep` |

O `ArcStatusChip` **reflete**; ele nunca **comanda**. Se o chip pudesse ser clicado para mudar de
estado, o estado deixaria de significar algo.

> No mockup interativo, um orquestrador simula esses sinais (conversas, jobs de fundo, quedas de
> link e recuperação) para que todos os estados apareçam sozinhos. Na aplicação real, o
> orquestrador é substituído por assinaturas no `EventBus` — nada mais muda.

---

## 2. Estados

Cada estado é um conjunto de **alvos contínuos**. O loop persegue esses alvos com aproximação
exponencial; nenhuma propriedade salta.

| Estado | `Glow` | `Spin` | `Core` | `Tint` | Chip |
|---|---|---|---|---|---|
| `Idle` | 0.62 | 1.00 | 1.00 | `Plasma` | Standby |
| `Listening` | 1.00 | 1.45 | 1.10 | `Plasma` | Listening |
| `Thinking` | 0.84 | **3.60** | 0.94 | `Arc` | Thinking |
| `Speaking` | 1.00 | 1.20 | 1.06 | `Ignition` | Speaking |
| `Warning` | 0.78 | 0.82 | 1.00 | `Caution` | Warning |
| `Error` | 0.92 | **0.28** | 0.88 | `Breach` | Fault |
| `Offline` | 0.14 | 0.12 | 0.78 | `Steel` | Offline |
| `Sleep` | 0.09 | 0.06 | 0.70 | `Steel` | Sleep |

### 2.1 Como cada propriedade lê

| Propriedade | Efeito visual |
|---|---|
| `Glow` | Intensidade do bloom, da nébula ambiente, da luz nas frestas das placas e do brilho das partículas |
| `Spin` | Multiplica **todas** as rotações de placas, bobinas e anéis HUD — mas **não** a varredura especular |
| `Core` | Escala do conjunto inteiro do reator |
| `Tint` | Interpolado canal a canal; nunca troca de cor por corte |

### 2.2 A varredura especular nunca para

O realce especular gira a `+14 °/s` escalado apenas por `lerp(0.35, 1, Glow)` — **independente
de `Spin`**. Consequência: mesmo em `Offline`, com as placas praticamente paradas, o metal
continua reluzindo levemente.

É isso que cumpre a regra "nada deve ficar completamente parado" sem trair a semântica de
"sistema desligado". Um reator imóvel leria como imagem estática; um reator girando leria como
online. A varredura resolve os dois.

### 2.3 Estados suplementares (componentes)

`Hover`, `Focus`, `Loading`, `Success` não são estados do reator — são estados de componente.
Ver [03-COMPONENTES](03-COMPONENTES.md).

| Estado | Onde vive |
|---|---|
| `Hover` | `ArcSectorHighlight` + escala do ícone |
| `Focus` | Mesmo setor anular — mouse e teclado compartilham o indicador |
| `Loading` | Arco de status do reator (1.70 R) alongando |
| `Success` | `ArcToast` com dot `Vital` |
| `WakeUp` | `Sleep` → `Idle` com surge; 900ms |

---

## 3. Microinterações

### 3.1 Surge de transição

**Toda** mudança de estado dispara uma onda de choque: um anel que expande de `1.3 R` a `3.4 R`
com `cubic-out`, decaindo em ~900ms.

```csharp
if (surge > 0.001f) {
    float e = 1f - MathF.Pow(1f - surge, 3f);
    DrawRing(R * Lerp(1.3f, 3.4f, e),
             width: (1f - surge) * 2.4f + 0.4f,
             alpha: (1f - surge) * 0.42f);
}
surge = MathF.Max(0f, surge - dt * 1.1f);
```

É a confirmação visual de que **algo mudou**, mesmo quando o usuário não estava olhando o chip.

### 3.2 Proximidade do cursor

| Distância do centro | Reação |
|---|---|
| `> 3.6 R` | Nenhuma |
| `3.6 R → 1.0 R` | `Proximity` sobe 0 → 1 com taxa 6.0 |
| Sobre o reator | Núcleo quente cresce 10%; escala do conjunto +4%; cursor ×1.5 |

O reator **sente** a aproximação antes do clique. É o que o faz parecer vivo em vez de decorativo.

### 3.3 Energia nas bobinas

Cada uma das 8 bobinas carrega um pulso viajando do raio interno ao externo, defasado por bobina:

```csharp
float phase = (t * 0.55f * spin + i / (float)count) % 1f;
float r     = Lerp(rIn, rOut, phase);
float fade  = MathF.Sin(phase * MathF.PI);   // acende e apaga nas pontas
```

Em `Thinking` (`Spin` 3.6) os pulsos disparam — é a leitura mais imediata de "processando".

### 3.4 Hover do setor anular

O setor **desliza** entre módulos pelo caminho angular mais curto, taxa 11.0:

```csharp
float diff = ((target - current + MathF.PI * 3f) % TAU) - MathF.PI;
current += diff * (1f - MathF.Exp(-11f * dt));
```

Sem o cálculo de caminho mais curto, ir do módulo 12 para o 1 faria o setor atravessar a tela
inteira ao contrário.

### 3.5 Entrada escalonada da órbita

Item `i` de `n` parte com 18% de atraso proporcional. Ver
[03-COMPONENTES §5](03-COMPONENTES.md#5--arcradialmenu).

### 3.6 Respiração

| Elemento | Período | Amplitude |
|---|---|---|
| Nébula ambiente | 11.4s | ±15% de `Glow` |
| Arco de status | 15.0s | 30° ↔ 96° de extensão |
| Dot do chip | 3.2s | opacidade 0.45 ↔ 1.0 |
| Partículas | 3.9s, fase aleatória | opacidade ±45% |

Períodos deliberadamente **incomensuráveis** — nunca sincronizam, então o olho não encontra
padrão e a cena não parece um loop.

### 3.7 Transcrição digitada

Em `Listening` e `Speaking`, o texto aparece caractere a caractere: 46ms/char para o que foi
ouvido, 28ms/char para a resposta. A fala chega mais rápido do que a escuta — inverter isso
faz a IA parecer lenta.

### 3.8 Ripple de toque

Toque no reator ou em um módulo: anel de `1.4 R` a `3.6 R`, `cubic-out`, ~670ms, `Ignition`.

---

## 4. Curvas e regras

Ver [01-TOKENS §6](01-TOKENS.md#6-movimento) para curvas, durações e taxas.

### 4.1 Regras invioláveis

1. **60 FPS ou reduza a cena**, nunca a suavidade. Ver [07-CHECKLISTS §2](07-CHECKLISTS.md#2-performance).
2. **Nenhuma propriedade contínua usa animação com duração.** Use aproximação exponencial — ela
   absorve mudanças de alvo no meio do caminho sem descontinuidade.
3. **Nenhuma transição é instantânea.** Mínimo 120ms, inclusive mudança de cor em hover.
4. **`prefers-reduced-motion` desliga rotação, partículas e varredura**, mantendo mudanças de
   opacidade e cor. O sistema continua legível e comunicativo, apenas parado.
5. **Nada é puramente decorativo em movimento.** Cada animação codifica um estado real: velocidade
   = carga, brilho = atividade, cor = saúde.
