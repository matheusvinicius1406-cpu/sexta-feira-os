# ADR-0010: Time Tracker — onde o tempo do dono vai, ligado aos objetivos

> **ADR.** Rastreio de tempo (ideia do Pulse), integrado ao Planning e ao World Model. Ver
> ADR-0001 (World Model), ADR-0002 (Eventos), ADR-0003 (Planning).

- **Número:** 0010 · **Data:** 2026-07-19 · **Estado:** `Aceito`
- **Autor:** Claude Code · **Aprovado por:** Proprietário ("faça logo tudo em sequência")

## Contexto e problema

Faltava saber **onde o tempo vai** — e conectar isso aos objetivos. Como rastrear tempo de
forma determinística, sem spans órfãos, e mantendo o presente ciente da atividade atual?

## Decisão

Modelo `TimeEntry` (com `goal_id` opcional → Planning) e serviço `TimeTracker` com **um único
timer ativo**: iniciar um novo **fecha** o aberto (sem órfãos). Um **relógio injetável** torna
as durações exatas em teste. Enquanto um timer roda, o **World Model** carrega
`atividade_atual`; ao parar, esquece. Publica `tempo.iniciado` / `tempo.parado`. `summary`
agrega segundos por rótulo. Objetivo inexistente: mantém o rótulo, descarta o vínculo (sem
erro).

Preserva "só meu", determinismo e substituibilidade.

## Consequências

- **Positivas:** tempo por objetivo/atividade; o presente sabe o que o dono faz agora; base
  para relatórios e para o briefing.
- **Custos:** uma tabela (migração compartilhada).
- **Reversão:** remover router/wiring; tabela cai via `downgrade`.

## Notas

`models.TimeEntry`, `app/timetrack/service.py`, `app/api/routers/timetrack.py`, migração
`5a60d68e75fa`, testes `tests/test_life.py`. CI verde (115 passed).
