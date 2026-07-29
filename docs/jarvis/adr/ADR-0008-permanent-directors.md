# ADR-0008: Diretores Permanentes — especialistas que acumulam expertise

> **Architecture Decision Record.** Formaliza os "Diretores" do Agent System: agentes
> permanentes com memória especializada própria, subordinados ao Kernel. Ver
> `../architecture/AGENT_SYSTEM.md`, Constituição (Art. IV/V) e ADR-0001..0007.

- **Número:** 0008
- **Título:** DirectorService — gabinete de especialistas permanentes com memória própria
- **Data:** 2026-07-19
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário ("diretores permanentes")
- **Documentos afetados:** `../architecture/AGENT_SYSTEM.md`

## Contexto

O Agent System previa dois tipos de agente: **temporários** (existiam — `SubAgentRunner`) e
**Diretores permanentes** (`[FUTURO]`) — especialistas que persistem, acumulam expertise e
recebem delegações do Kernel. *"O aprendizado permanece no Diretor responsável."*

## Problema

Como criar especialistas persistentes com memória própria, sem duplicar infraestrutura de
memória, sem quebrar as regras de segurança dos agentes (toolset restrito, sem recursão,
owner-scoped, local) e mantendo o Kernel como único ponto de decisão?

## Decisão

Modelo `Director` (upsert por dono+nome; `title`, `domain`, `allowed_tools` opcional) e
serviço `DirectorService` (`app/directors/service.py`):

- **Gabinete canônico** semeado de forma idempotente (`ensure_defaults`): engenharia,
  pesquisa, segurança, memória, automação, aprendizagem, dispositivos — o dono adiciona mais
  (ex.: jurídico) via API.
- **Memória especializada no mesmo substrato:** expertise = linhas de `Memory` com
  `source='director:<nome>'` — mesmas políticas de privacidade/curadoria do grafo, zero
  tabelas de memória paralelas. A expertise é **injetada no contexto** do diretor na próxima
  delegação.
- **Delegação:** persona (título + domínio + expertise) → loop de tools **restrito**
  (`allowed_tools` do diretor, default = subset de sub-agente) → resultado → **consolidação**
  (o cérebro local destila a lição em 1 frase e a grava na memória do diretor — "o
  aprendizado permanece no Diretor").
- **Segurança em código:** `delegate`/`consult_director` são **hard-stopped** dentro do loop
  (sem recursão), tudo owner-scoped, modelo local. Eventos `diretor.delegado` /
  `diretor.concluido` (auditável).
- Kernel delega via tool **`consult_director`**; sub-agentes temporários continuam via
  `delegate`.

### Correção de bug incluída

O `SubAgentRunner` chamava `specs_subset` (async) **sem await** — sub-agentes rodavam sem
ferramenta nenhuma (era o `RuntimeWarning` da suíte). Corrigido; o warning sumiu. O hard-stop
de recursão dos sub-agentes agora bloqueia também `consult_director`.

Preserva os invioláveis: **"só meu"**, **hierarquia de autoridade** (Diretores subordinados ao
Kernel; nunca agem sem delegação), **substituibilidade**, **auditabilidade**.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Director + expertise no substrato de Memory (escolhida)** | persiste, acumula, mesmas políticas, sem infra nova | recall da expertise é por recência (não semântico) na v1 | — |
| Tabela de memória própria por diretor | isolamento | duplica substrato; contraria MEMORY_ARCHITECTURE ("mesmo substrato") | rejeitada |
| Só sub-agentes temporários | já existia | expertise evapora a cada uso; viola o Agent System | rejeitada |
| Diretores como processos/modelos separados | isolamento forte | pesado para um dono; desnecessário no MVP | rejeitada (futuro possível) |

## Consequências

- **Positivas:** especialistas que melhoram com o uso; o Kernel delega por domínio; trilha de
  eventos por delegação; o dono ensina diretores diretamente (`POST .../memory`).
- **Custos:** uma tabela + migração; uma inferência extra (consolidação) por delegação.
- **Neutras:** tool `consult_director`, router `/api/v1/directors`.

## Riscos e mitigação

- **Risco:** expertise crescer sem curadoria → **Mitigação:** vive no grafo de memória — a
  curadoria soberana (inspecionar/editar/esquecer) já cobre; limite de 12 itens no contexto.
- **Ponto de reversão:** remover tool/router/wiring; a tabela `directors` cai via
  `downgrade`; a expertise permanece como memória comum (inofensiva).

## Notas de implementação

`models.Director`, `app/directors/service.py`, migração `4ff8124a11d4`,
`app/api/routers/directors.py`, tool `consult_director` + fix em `brain/subagents.py`,
wiring em `core/di.py`, testes `tests/test_directors.py`. CI verde: ruff + alembic + pytest
(105 passed, warning antigo eliminado).
