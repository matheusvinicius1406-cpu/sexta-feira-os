# ADR-0002: Barramento de Eventos como espinha dorsal de comunicação

> **Architecture Decision Record.** Segundo pilar estrutural da transformação em direção ao
> North Star. Ver `../architecture/EVENT_ARCHITECTURE.md` e ADR-0001 (World Model).

- **Número:** 0002
- **Título:** Introduzir um EventBus persistido e o mapeamento evento → World Model
- **Data:** 2026-07-18
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário (escolheu seguir para a Etapa 2)
- **Documentos afetados:** `../architecture/EVENT_ARCHITECTURE.md`, `../architecture/WORLD_MODEL.md`

## Contexto

Após o ADR-0001, o Kernel tem um World Model explícito, mas ele só era atualizado por
chamada direta (tools/API). O North Star exige o modelo **event-driven**: *"Toda comunicação
ocorre por eventos. Cada evento atualiza o estado do Kernel."* Não havia barramento de
eventos nem trilha de auditoria de eventos.

## Problema

Como introduzir um backbone publish/subscribe que (a) persista eventos como trilha de
auditoria, (b) atualize o World Model, (c) seja idempotente e ordenado, (d) isole
assinantes que falham — sem acoplar ao modelo de IA e sem quebrar o que já roda?

## Decisão

Introduzir o modelo `Event` (imutável; `type`, `source`, `payload`, `correlation_id`,
`idempotency_key`, `sequence` por dono, `status`) e o serviço `EventBus`
(`app/events/bus.py`): `subscribe(pattern)` com glob (`exato` | `prefixo.*` | `*`),
`publish(...)` (persiste → sequência → despacho determinístico) e `history(...)`.

Um assinante built-in, `WorldModelProjector`, mapeia eventos curados
(`localizacao.mudou`, `usuario.acordou`, `dispositivo.conectado`, `saude.batimento_elevado`…)
para fatos do World Model, e qualquer evento pode setar um fato via `world_key`/`world_value`.
O **Scheduler** passa a publicar `agendamento.venceu` quando dispara — *tempo vira evento*.

**Garantias implementadas:** auditabilidade (todo evento é persistido, mesmo com assinante
falho), idempotência (`idempotency_key`), ordenação/correlação (`sequence` por dono +
`correlation_id`), degradação graciosa (exceção de um assinante é isolada; não corrompe o
evento nem bloqueia os demais).

Preserva os invioláveis: **"só meu"** (local, escopado ao dono), **Kernel independente do
modelo** (o barramento é infra; o LLM não participa), **substituibilidade** (o despacho
in-process pode virar fila/broker atrás do mesmo contrato).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **EventBus persistido + projetor (escolhida)** | auditável, idempotente, substituível, determinístico p/ testes | despacho síncrono no MVP | — |
| Broker externo (Redis/NATS/Kafka) | escala, async real | dependência pesada; contraria offline-first/"só meu" p/ um dono | rejeitada (futuro possível atrás do contrato) |
| Só sinais em memória (sem persistir) | simples | sem trilha de auditoria; perde eventos em reinício | rejeitada |
| Atualizar World Model só por chamada direta | já existia | não é event-driven; não há backbone p/ Planning/Decision | rejeitada |

## Consequências

- **Positivas:** backbone event-driven; World Model reativo; trilha de auditoria de
  primeira classe; base para Planning/Decision (próximas etapas) e presença distribuída.
- **Custos:** uma tabela + migração; o despacho é síncrono (um assinante lento bloqueia o
  `publish` — aceitável no MVP local).
- **Neutras:** novo endpoint `/api/v1/events` (publicar/auditar).

## Riscos e mitigação

- **Risco:** assinante lento bloqueia o publish → **Mitigação (futuro):** fila assíncrona
  atrás do mesmo contrato do EventBus; hoje os assinantes são rápidos e isolados por
  try/except.
- **Ponto de reversão:** remover a subscrição do projetor e o hook do scheduler desliga o
  efeito; a tabela `events` cai via `downgrade`.

## Nota de teste (fragilidade corrigida)

A suíte dependia implicitamente de `test_kernel` rodar primeiro: cada módulo tinha seu
próprio `TestClient`, e o Kernel é singleton que fecha os clientes async no shutdown. Isso
foi corrigido com um `conftest.py` de **escopo de sessão** (um único lifespan da app para
toda a suíte). CI verde: ruff + alembic + pytest (57 passed).

## Notas de implementação

`models.Event`, `app/events/bus.py`, `app/events/projector.py`, migração `66911ff08226`,
`app/api/routers/events.py`, hook em `schedule/service.py` (`agendamento.venceu`), wiring em
`core/di.py`, testes `tests/test_events.py`, `tests/conftest.py`.
