# Arquitetura Orientada a Eventos

> A espinha dorsal de comunicação do JARVIS. Deriva de `ARCHITECTURAL_PRINCIPLES.md`
> (event-driven) e do `NORTH_STAR.md`. Estado: `[PARCIAL]` — o **EventBus** existe (ver
> **ADR-0002**): eventos persistidos (trilha de auditoria), `sequence` por dono,
> idempotência, degradação graciosa, assinatura por `exato`/`prefixo.*`/`*`, projeção no
> World Model, e o Scheduler publicando `agendamento.venceu` (tempo → evento); exposto em
> `/api/v1/events`. Ainda `[FUTURO]`: despacho **assíncrono** (fila/broker atrás do mesmo
> contrato) e sincronização **distribuída** entre corpos.

## Princípio

Toda comunicação relevante ocorre por **eventos**. Componentes **publicam** o que
aconteceu e **assinam** o que lhes interessa, em vez de se chamarem diretamente quando não
há necessidade de acoplamento temporal. **Cada evento atualiza o estado do Kernel** (World
Model) e pode disparar planejamento, memória, automações ou ações.

Benefícios: desacoplamento, extensibilidade (novos assinantes sem tocar nos produtores),
presença distribuída (o mesmo evento chega a qualquer corpo), e auditabilidade natural (o
fluxo é uma trilha de eventos).

## Exemplos de eventos

- `usuario.acordou`
- `localizacao.mudou`
- `documento.aberto`
- `projeto.compilado`
- `mensagem.recebida`
- `sensor.movimento`
- `saude.batimento_elevado`
- `dispositivo.conectado` / `dispositivo.desconectado`
- `tarefa.concluida` / `tarefa.falhou`
- `agendamento.venceu`

## Anatomia de um evento

Todo evento carrega, no mínimo: **tipo**, **origem** (qual corpo/sensor/serviço),
**timestamp**, **payload** e **correlação** (para rastrear um fluxo). Eventos são
**imutáveis** — descrevem algo que já ocorreu.

## Fluxo

```
Fonte (sensor / dispositivo / serviço / timer)
   ↓ publica
Barramento de Eventos
   ↓ entrega aos assinantes
Kernel (atualiza World Model) · Memória (episódica/temporal) · Regras/Automações
   ↓ se relevante
Planejamento → Decisão → Ação  (que, por sua vez, gera novos eventos)
```

## Papéis

- **Produtores:** dispositivos (via protocolo de ação), sensores, serviços, o próprio
  Kernel, o agendador (eventos temporais).
- **Barramento:** entrega confiável; permite tempo real (push) e histórico (para
  reprocessar/auditar). Implementação substituível atrás de um contrato.
- **Assinantes:** Kernel (World Model), Memória, motor de automações (n8n), políticas de
  segurança (detecção de anomalias), Diretores.

## Garantias e contratos

1. **Ordenação e correlação:** eventos de uma mesma origem preservam ordem suficiente para
   reconstruir o fluxo; a correlação liga causa e efeito.
2. **Idempotência:** assinantes toleram entrega duplicada sem corromper estado.
3. **Degradação graciosa:** um assinante lento/fora não bloqueia o barramento nem o Kernel.
4. **Auditabilidade:** o histórico de eventos é uma trilha de auditoria de primeira classe.
5. **Segurança:** eventos de dispositivos são autenticados (dispositivos pareados); nenhum
   evento não confiável altera o World Model sem validação.

## Presença distribuída

Como o estado cognitivo é único e os corpos são muitos, os eventos são o mecanismo que
mantém todos os dispositivos **sincronizados com a mesma mente**: um corpo publica, o
Kernel atualiza, e qualquer corpo reflete o novo estado. A sincronização entre corpos
ocorre pela rede privada do dono (local/túnel), nunca por nuvem pública.

## Relação com o Scheduler e as automações

- O **Task Scheduler** transforma tempo em eventos (`agendamento.venceu`) e reage a eventos
  para executar/pausar/repriorizar.
- O **n8n** assina eventos para disparar workflows e publica eventos de conclusão — como
  motor de execução, sem autoridade cognitiva.
