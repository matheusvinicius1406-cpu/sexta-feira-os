# ADR-0001: Introduzir o World Model e o User Model como estado explícito do Kernel

> **Architecture Decision Record.** Primeiro pilar estrutural da transformação do projeto
> em direção ao North Star. Ver `../constitution/DECISION_PROCESS.md` e
> `../architecture/WORLD_MODEL.md`.

- **Número:** 0001
- **Título:** World Model + User Model como estado explícito consultado em toda decisão
- **Data:** 2026-07-18
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário (escolheu esta etapa como ponto de partida)
- **Documentos afetados:** `../architecture/WORLD_MODEL.md`, `../architecture/COGNITIVE_KERNEL.md`

## Contexto

O código (`backend-core`) tinha memória persistente (grafo), cognição, tools, scheduler e
conectores — mas **não tinha World Model**. O contexto de cada decisão era implícito no
histórico da conversa (`cognition._build_messages`). O North Star exige o oposto: *"Nenhuma
solicitação começa do zero. Toda decisão considera o World Model completo."*

## Problema

Como dar ao Kernel um **estado explícito do presente** (o "agora") e um **modelo do dono**
(ao longo do tempo), consultado em toda interação, sem acoplar isso ao modelo de IA e sem
quebrar o que já funciona?

## Decisão

Introduzir dois armazenamentos tipados, escopados ao dono, **upsert por chave**:

- **World Model** (`WorldFact`): o presente — uma verdade corrente por chave
  (`foco_atual`, `dispositivos_online`, `humor`…), com `category`, `source`, `confidence` e
  `is_inference`.
- **User Model** (`UserAttribute`): o dono ao longo do tempo — traços duráveis por chave
  (`estilo_programacao`, objetivos, hábitos, projetos).

Ambos atrás de um contrato único, o serviço `WorldModel` (`app/world/service.py`):
`set_fact/get_fact/forget_fact/snapshot`, `set_attribute/.../profile` e, crucialmente,
`context_digest`, que o `Context Manager` (`cognition._build_messages`) injeta na persona a
cada turno. Inferências são **rotuladas** ("(inferência)"), nunca apresentadas como fato.

A decisão **preserva os princípios invioláveis**:
- **"só meu":** tudo local, escopado ao dono; nenhum dado sai; nenhuma LLM na nuvem.
- **Kernel independente do modelo:** o World Model é dado + contrato; o LLM apenas o lê/atualiza
  via tools (`remember_context`, `remember_about_me`) — trocar o modelo não muda nada disto.
- **Substituibilidade:** o armazenamento (SQLite hoje) é trocável atrás do serviço `WorldModel`.
- **Soberania/auditabilidade:** o dono inspeciona, edita e esquece qualquer entrada via
  `/api/v1/world`.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Tabelas tipadas + serviço (escolhida)** | explícito, auditável, substituível, testável | duas tabelas novas | — |
| Manter contexto implícito no histórico | zero código | viola o North Star; não é consultável nem auditável; "começa do zero" | rejeitada |
| Guardar tudo como `Memory` (grafo) | reusa infra | mistura passado (memória) com presente (World Model); sem upsert por chave; sem "agora" claro | rejeitada |
| Cache em memória (sem persistir) | rápido | perde o estado em reinício; fere persistência cognitiva | rejeitada |

## Consequências

- **Positivas:** o Kernel passa a ter um "agora" explícito injetado em toda decisão; base para
  o Planning/Decision Engines e para a atualização por eventos (próximas etapas).
- **Custos:** duas tabelas + uma migração; o digest adiciona tokens ao prompt (limitado a
  12+12 entradas).
- **Neutras:** duas novas tools disponíveis ao modelo.

## Riscos e mitigação

- **Risco:** o digest crescer e poluir o contexto → **Mitigação:** limites (`max_world`,
  `max_user`) e ordenação por mais recente.
- **Ponto de reversão:** remover a injeção em `_build_messages` e as tools desliga o efeito
  sem migração destrutiva; as tabelas podem cair via `downgrade`.

## Notas de implementação

`app/world/service.py`, `app/world/__init__.py`, modelos `WorldFact`/`UserAttribute`,
migração `8523e5bdf35e`, router `app/api/routers/world.py`, tools `remember_context` /
`remember_about_me`, testes `tests/test_world.py`. CI verde (ruff + alembic + pytest).
