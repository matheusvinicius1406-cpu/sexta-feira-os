# ADR-0003: Planning Engine — o sistema trabalha por objetivos

> **Architecture Decision Record.** Terceiro pilar estrutural rumo ao North Star. Ver
> `../architecture/COGNITIVE_KERNEL.md`, ADR-0001 (World Model) e ADR-0002 (EventBus).

- **Número:** 0003
- **Título:** Motor de planejamento com objetivos, decomposição, dependências e progresso
- **Data:** 2026-07-18
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário ("comece a etapa 3")
- **Documentos afetados:** `../architecture/COGNITIVE_KERNEL.md`, `../architecture/NORTH_STAR.md`

## Contexto

O North Star diz: *"O sistema trabalha por objetivos. Objetivos possuem prioridade, prazo,
dependências, progresso, histórico. Grandes objetivos são divididos automaticamente em
subtarefas."* Após os ADR-0001 (World Model) e 0002 (EventBus), faltava o motor que
representa e move objetivos.

## Problema

Como modelar objetivos com prioridade/prazo/dependências/progresso e decomposição em
subtarefas, integrando aos eventos (Etapa 2) e ao World Model (Etapa 1), sem acoplar ao
modelo de IA?

## Decisão

Introduzir os modelos `Goal` (auto-referência `parent_id` para subtarefas; `priority`,
`status`, `progress`, `due_at`) e `GoalDependency` (aresta "X depende de Y"), e o serviço
`PlanningEngine` (`app/planning/service.py`): `create_goal`, `decompose`, `add_dependency`,
`set_progress`, `complete`, `cancel`, `list_goals`.

Regras determinísticas: o progresso do pai é a **média** dos filhos (roll-up); um objetivo
fica **`blocked`** enquanto tiver dependência não concluída; concluir um objetivo
**desbloqueia** os dependentes. A *decisão* de como dividir um objetivo é do cérebro (via a
tool `decompose_goal`, que passa a lista de subtarefas); o engine só executa de forma
determinística.

Integração com os pilares anteriores:
- **Eventos (ADR-0002):** publica `objetivo.criado`, `objetivo.concluido`,
  `tarefa.desbloqueada` — trilha de auditoria + reatividade.
- **World Model (ADR-0001):** mantém `objetivos_ativos` e `objetivo_atual` como "o presente"
  do que o dono persegue.

Preserva os invioláveis: **"só meu"** (local, escopado ao dono), **Kernel independente do
modelo** (o engine é lógica determinística; o LLM apenas o aciona por tools),
**substituibilidade** (contrato estável do `PlanningEngine`).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Goal + GoalDependency + engine determinístico (escolhida)** | explícito, testável, integra eventos/World Model | mais um par de tabelas | — |
| Reusar `ScheduledTask` para objetivos | reusa infra | tempo ≠ objetivo; sem dependências/hierarquia/progresso | rejeitada |
| Deixar o LLM "planejar" sem persistência | zero schema | sem progresso/dependências reais; não sobrevive a reinício; não auditável | rejeitada |
| Decomposição automática só via LLM no engine | menos tools | acopla o engine ao modelo; quebra "independente do modelo" | rejeitada (LLM decide via tool; engine executa) |

## Consequências

- **Positivas:** objetivos de primeira classe com dependências e progresso; base para o
  Decision Engine (Etapa 4) priorizar sob restrições; o World Model reflete o foco atual.
- **Custos:** duas tabelas + migração; roll-up recalcula a média dos filhos a cada mudança.
- **Neutras:** 4 tools novas (`create_goal`, `decompose_goal`, `list_goals`, `complete_goal`)
  e o router `/api/v1/planning`.

## Riscos e mitigação

- **Risco:** ciclos de dependência → **Mitigação:** bloqueio é calculado por dependências não
  concluídas; um ciclo simplesmente mantém ambos bloqueados (não trava o sistema). Detecção
  explícita de ciclos fica para uma iteração futura.
- **Ponto de reversão:** remover o router/tools e a subscrição; as tabelas caem via
  `downgrade`.

## Notas de implementação

`models.Goal`, `models.GoalDependency`, `app/planning/service.py`, migração `061b41441193`,
`app/api/routers/planning.py`, tools em `brain/tools.py`, wiring em `core/di.py`, testes
`tests/test_planning.py`. CI verde: ruff + alembic + pytest (66 passed).
