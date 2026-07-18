# ADR-0004: Decision Engine — escolha sob restrições, determinística e auditável

> **Architecture Decision Record.** Quarto pilar estrutural rumo ao North Star; fecha o
> quarteto World Model / Eventos / Planning / Decision. Ver
> `../architecture/COGNITIVE_KERNEL.md` e ADR-0001..0003.

- **Número:** 0004
- **Título:** Motor de decisão que escolhe entre alternativas sob políticas
- **Data:** 2026-07-18
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário ("comece a fase 4")
- **Documentos afetados:** `../architecture/COGNITIVE_KERNEL.md`, `../architecture/NORTH_STAR.md`

## Contexto

O North Star lista o **Decision Engine** entre os subsistemas: *"escolha entre alternativas
sob restrições"*. Após World Model (ADR-0001), Eventos (ADR-0002) e Planning (ADR-0003),
faltava o motor que escolhe — e que explique o porquê ("por que o JARVIS fez X?").

## Problema

Como escolher, de forma **determinística e auditável**, a próxima ação/objetivo entre
alternativas, considerando prioridade, prazo, andamento e o estado do dono — sem que o LLM
seja quem decide (preservando o Kernel independente do modelo)?

## Decisão

Introduzir o modelo `Decision` (question, policy, chosen, rationale, options JSON —
auditável) e o serviço `DecisionEngine` (`app/decision/service.py`):

- `score_options(options, weights)` — **primitiva pura**: soma ponderada de critérios
  normalizados (0..1), ordenada, com desempate determinístico por rótulo.
- `decide_next_goal(db, owner_id)` — reúne os objetivos abertos (Planning), calcula critérios
  (`priority`, `urgency` pelo prazo, `momentum` pelo progresso), aplica a **política**,
  escolhe, persiste a `Decision`, emite `decisao.tomada` e grava `foco_decidido` no World
  Model.

A **política** adapta-se ao presente: se o World Model indica energia baixa (`humor`/`energia`
= "cansado"/"baixa"…), os pesos favorecem terminar o que está quase pronto (`momentum`); caso
contrário, prioridade domina. O **LLM não decide**: ele apenas *consulta* via a tool
`decide_next` e recebe uma escolha explicável.

Preserva os invioláveis: **"só meu"** (local, escopado ao dono), **Kernel independente do
modelo** (lógica determinística; o LLM só aciona), **substituibilidade** (contrato estável;
os pesos/critérios podem evoluir sem mudar os chamadores), **auditabilidade** (toda decisão
é registrada com rationale e alternativas).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Scoring determinístico + política + persistência (escolhida)** | explicável, testável, auditável, usa World Model/Planning | pesos são heurística inicial | — |
| Deixar o LLM escolher livremente | flexível | não determinístico, não auditável, acopla decisão ao modelo | rejeitada |
| Regras fixas (if/else) sem pesos | simples | rígido; não pondera múltiplos critérios nem adapta ao estado | rejeitada |
| Otimização/solver | ótimo teórico | complexidade/dependência desproporcional para um dono | rejeitada (futuro possível atrás do contrato) |

## Consequências

- **Positivas:** o Kernel escolhe de forma explicável; fecha o loop cognitivo (contexto →
  planejamento → decisão); trilha de auditoria de decisões.
- **Custos:** uma tabela + migração; os pesos são uma política inicial a calibrar.
- **Neutras:** tool `decide_next` e router `/api/v1/decision`.

## Riscos e mitigação

- **Risco:** pesos mal calibrados → escolhas ruins → **Mitigação:** decisão é auditável
  (rationale + options), fácil de inspecionar e ajustar; a primitiva de scoring é isolada e
  testada.
- **Ponto de reversão:** remover a tool/router; a tabela `decisions` cai via `downgrade`.

## Notas de implementação

`models.Decision`, `app/decision/service.py`, migração `194495cbd525`,
`app/api/routers/decision.py`, tool `decide_next` em `brain/tools.py`, wiring em `core/di.py`,
testes `tests/test_decision.py`. CI verde: ruff + alembic + pytest (75 passed).
