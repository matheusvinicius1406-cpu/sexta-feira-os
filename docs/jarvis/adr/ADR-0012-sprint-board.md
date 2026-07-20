# ADR-0012: Sprint Board — visão de quadro sobre os objetivos

> **ADR.** Última função inspirada no Pulse: um quadro (kanban) sobre o Planning Engine.
> Ver ADR-0003 (Planning). Fecha as "built-in tools" do Pulse compatíveis com o kernel.

- **Número:** 0012 · **Data:** 2026-07-19 · **Estado:** `Aceito`
- **Autor:** Claude Code · **Aprovado por:** Proprietário ("termine as funções do pulse")

## Contexto e problema

Das built-in tools do Pulse (git, diff viewer, daily briefing, goals, sprint board,
journal, habits, time tracker), só faltava o **sprint board**. Como oferecer uma visão de
quadro sem duplicar dados nem criar um "app" separado?

## Decisão

Um **read-model** sobre o Planning Engine: `PlanningEngine.board(db, owner_id)` agrupa os
objetivos em colunas por status — **backlog** (pending), **fazendo** (active), **bloqueado**
(blocked), **concluído** (done) — ordenadas por prioridade, com estatísticas (contagens,
`open`, `avg_open_progress`). Cancelados ficam fora. Sem tabela nova, sem migração.

Exposto em `GET /api/v1/planning/board` e pela tool `sprint_board`. Preserva "só meu"
(dados locais), determinismo e substituibilidade.

### Sobre git / diff viewer (fora do kernel, de propósito)

As outras built-in tools do Pulse — **git** e **diff viewer** — são ferramentas de
desenvolvimento e **não** entram no kernel cognitivo privado: dar ao cérebro acesso a
git/filesystem ampliaria a superfície de segurança e contraria a separação de camadas.
Esse papel já pertence à **fábrica de desenvolvimento (n8n + runner)**, construída à parte.
Se desejado no futuro, uma capacidade **read-only** de "status do projeto" pode ser um
conector (ADR próprio), nunca acesso direto do modelo ao git.

## Consequências

- **Positivas:** visão de sprint imediata sobre os objetivos; base para UI (app Android) e
  para o briefing.
- **Custos:** nenhum (visão sobre dados existentes).
- **Reversão:** remover o método/rota/tool; nada a migrar.

## Notas

`PlanningEngine.board`, rota em `app/api/routers/planning.py`, tool `sprint_board`, testes em
`tests/test_planning.py`. Sem migração. CI verde: ruff + alembic + pytest (136 passed).
