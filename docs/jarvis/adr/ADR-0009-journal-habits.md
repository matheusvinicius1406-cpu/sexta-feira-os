# ADR-0009: Journal + Habits — diário e hábitos ligados aos pilares

> **ADR.** Primitivas de produtividade pessoal (ideia do Pulse), integradas aos pilares em
> vez de isoladas. Ver ADR-0001 (World Model), ADR-0002 (Eventos), ADR-0007 (Extrator).

- **Número:** 0009 · **Data:** 2026-07-19 · **Estado:** `Aceito`
- **Autor:** Claude Code · **Aprovado por:** Proprietário ("faça logo tudo em sequência")

## Contexto e problema

O North Star quer um segundo cérebro que acompanha a vida do dono. Faltavam **diário** e
**hábitos** — e a memória procedural (`MEMORY_ARCHITECTURE.md`) estava `[FUTURO]`. Como
adicioná-los sem virar um app de notas solto?

## Decisão

Modelos `JournalEntry`, `Habit`, `HabitCheck` e os serviços `JournalService` / `HabitService`:

- **Diário:** cada entrada publica `diario.registrado` e (best-effort) passa pelo
  **MemoryExtractor** — fatos duráveis vão ao grafo e ao User Model. Uma falha do extrator
  nunca perde a entrada.
- **Hábitos:** check-in **idempotente por dia** (`UniqueConstraint(habit_id, day)`); o
  **streak** é calculado de forma determinística a partir dos checks e refletido no **World
  Model** (`habito:<nome>` = "streak de N dias") — o presente sabe. Publica `habito.marcado`.

Preserva "só meu" (local, escopado ao dono) e a substituibilidade.

## Consequências

- **Positivas:** memória procedural começa a existir; o briefing e o User Model ganham sinais
  de rotina; streaks no presente.
- **Custos:** três tabelas (migração compartilhada com ADR-0010/0011).
- **Reversão:** remover routers/wiring; tabelas caem via `downgrade`.

## Notas

`models.JournalEntry/Habit/HabitCheck`, `app/journal/service.py`,
`app/api/routers/journal.py`, migração `5a60d68e75fa`, testes `tests/test_life.py`. CI verde
(115 passed).
