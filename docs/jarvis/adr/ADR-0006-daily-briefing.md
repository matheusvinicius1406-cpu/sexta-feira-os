# ADR-0006: Daily Briefing — o reporte proativo que amarra os cinco pilares

> **Architecture Decision Record.** Capstone que integra World Model / Eventos / Planning /
> Decision / Learning num único produto diário. Conceito inspirado (reimplementado) no
> "daily briefing" local-first. Ver ADR-0001..0005.

- **Número:** 0006
- **Título:** Serviço de briefing (reporte diário/sob demanda) sobre os cinco pilares
- **Data:** 2026-07-18
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário (escolheu "Daily Briefing" entre as ideias do Pulse)
- **Documentos afetados:** `../architecture/COGNITIVE_KERNEL.md`, `../architecture/NORTH_STAR.md`

## Contexto

O North Star quer um sistema **proativo** que *"antecipa necessidades"*. Após construir os
cinco pilares, faltava a experiência diária que os torna tangíveis — o "reports back every
morning". A ideia veio de um produto local-first (Pulse/Vaylo Studios); **copiamos apenas o
conceito**, não marca, textos, visual ou código.

## Problema

Como produzir um resumo proativo (o "segundo cérebro reportando") que una o estado atual, os
objetivos, o foco, os eventos e os aprendizados — de forma **local, determinística e
agendável** — sem depender do modelo de IA?

## Decisão

Modelo `Briefing` (kind daily|on_demand, summary, content JSON) e serviço `BriefingService`
(`app/briefing/service.py`) que monta, **só de dados locais**, seis seções: presente (World
Model), dono (User Model), objetivos abertos (Planning), foco sugerido (Decision), eventos
recentes (EventBus) e aprendizados (Learning). A montagem é **determinística** (funciona
offline, testável); um LLM pode narrar depois, mas o conteúdo nunca depende dele.

Proatividade real: o **Scheduler** ganhou `kind="briefing"` — um `ScheduledTask` recorrente
(24h) gera o briefing e o entrega via protocolo de ação (`notify`) ao corpo do dono. Endpoint
`POST /api/v1/briefing/schedule` agenda o "reporte de toda manhã".

Preserva os invioláveis: **"só meu"** (montado apenas de dados locais; nada sai), **Kernel
independente do modelo**, **degradação graciosa** (cada seção some se o pilar faltar),
**substituibilidade**.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Serviço de briefing determinístico + agendável (escolhida)** | local, testável, integra os 5 pilares, proativo | montagem fixa (heurística de render) | — |
| Deixar o LLM gerar o resumo do zero | narrativa rica | não determinístico, exige modelo online, difícil de testar | rejeitada (LLM pode narrar por cima, opcional) |
| Só um endpoint de "status" sem persistir | simples | sem histórico de reportes, sem proatividade | rejeitada |
| Copiar features do Pulse (código/UX) | — | é produto fechado; copiar marca/UX é indevido; sem código aberto | rejeitada (copiamos só a ideia) |

## Consequências

- **Positivas:** o segundo cérebro passa a "reportar" — capstone tangível que exercita os
  cinco pilares juntos; base para voz ("me dá o briefing") e para o app.
- **Custos:** uma tabela + migração; o Scheduler ganhou um novo `kind`.
- **Neutras:** tool `daily_briefing` e router `/api/v1/briefing`.

## Riscos e mitigação

- **Risco:** gerar briefing chama `decide_next_goal`, que persiste uma decisão →
  **Mitigação:** é semanticamente correto (decidir o foco do dia) e auditável; se virar ruído,
  um `preview` sem persistência pode ser adicionado atrás do contrato.
- **Ponto de reversão:** remover o `kind="briefing"` do Scheduler, a tool e o router; a tabela
  `briefings` cai via `downgrade`.

## Nota de atribuição

Conceito de "daily briefing local-first" inspirado no **Pulse (Vaylo Studios)**. Apenas a
**ideia** foi adaptada; nenhum código, marca, texto ou design foi copiado. Ideias não são
protegidas por direitos autorais; a implementação é integralmente nossa.

## Notas de implementação

`models.Briefing`, `app/briefing/service.py`, migração `e43ada9059a7`,
`app/api/routers/briefing.py`, `kind="briefing"` em `schedule/service.py`, tool
`daily_briefing`, wiring em `core/di.py`, testes `tests/test_briefing.py`. CI verde: ruff +
alembic + pytest (87 passed).
