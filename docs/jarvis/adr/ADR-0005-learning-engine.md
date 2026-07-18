# ADR-0005: Learning Engine — aprendizado contínuo (adaptado do OpenJarvis)

> **Architecture Decision Record.** Quinto pilar. Formaliza o ciclo de aprendizado do North
> Star, reimplementado na nossa arquitetura a partir de um conceito do OpenJarvis (Apache-2.0).
> Ver `../architecture/COGNITIVE_KERNEL.md` e ADR-0001..0004.

- **Número:** 0005
- **Título:** Motor de aprendizado contínuo (observar → avaliar → registrar → adaptar)
- **Data:** 2026-07-18
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário ("copie o que agrega... refaça de forma que satisfaça o 'só meu'")
- **Documentos afetados:** `../architecture/COGNITIVE_KERNEL.md`, `../architecture/MEMORY_ARCHITECTURE.md`

## Contexto

O North Star descreve o **Aprendizado Contínuo**: *"Executar → Observar resultado → Avaliar
qualidade → Registrar aprendizado → Atualizar memória → Atualizar comportamento futuro."*
Existia só um `_auto_learn` parcial na cognição.

Ao analisar o repositório **OpenJarvis** (open-jarvis/OpenJarvis, Apache-2.0), o único
subsistema com design **sólido e compatível** com o nosso é o loop de aprendizado
(`learning_orchestrator.py`: trace → learn → evaluate → gate). O resto foi **rejeitado por
princípio**: o `engine/` é fortemente acoplado a LLMs de nuvem (viola "sem LLM na nuvem") e há
um subsistema `mining/` que submete shares a um pool do operador (viola "só meu" e usaria o
hardware do dono para terceiros).

## Problema

Como ter um motor de aprendizado contínuo, aproveitando o design sólido do OpenJarvis, **sem**
copiar seu código de nuvem/mining e **sem** dar a terceiros acesso a hardware, dados ou rede —
preservando "só meu" e o Kernel independente do modelo?

## Decisão

**Reimplementar o conceito** (não copiar arquivos) na nossa arquitetura: modelo `Learning`
(kind, tag, ref_id, context, observation, quality 0..1, lesson) e serviço `LearningEngine`
(`app/learning/service.py`) com `record`, `observe_decision`, `lessons`, `stats`.

O diferencial — e o que nos torna **mais coeso que o original** — é a conexão com os pilares
que já temos:
- a **lição durável** vai para a **Memória** em grafo (resurge no recall);
- uma **dificuldade recorrente** (mesma `tag` com baixa qualidade ≥2×) vira atributo no
  **User Model** (o comportamento se adapta);
- todo registro publica **`aprendizado.registrado`** no **EventBus** (auditoria + reatividade);
- `observe_decision` fecha o laço com o **Decision Engine** (feedback sobre decisões passadas).

**Nada de nuvem, mining, telemetria ou chamadas externas.** O LLM apenas aciona via tools
(`record_learning`, `recall_lessons`); a lógica é determinística.

### Atribuição (Apache-2.0)

O design do laço trace→learn→evaluate é inspirado no **OpenJarvis** (open-jarvis/OpenJarvis),
licenciado sob **Apache License 2.0**. Nenhum arquivo/código-fonte foi copiado; o conceito foi
reimplementado. Crédito registrado aqui e nos docstrings dos módulos (`models.Learning`,
`app/learning/service.py`).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Reimplementar o conceito na nossa arquitetura (escolhida)** | limpo, "só meu", integrado aos pilares, sem superfície de terceiros | escrever do zero | — |
| Copiar `learning/` do OpenJarvis e remendar | mais rápido | arrasta abstrações/config deles; superfície não revisada; risco de puxar nuvem | rejeitada |
| Adotar o framework OpenJarvis inteiro | "pronto" | traz engine de nuvem + mining; viola princípios invioláveis | rejeitada |
| Só manter o `_auto_learn` atual | zero código | não é o ciclo completo; sem qualidade/lições/adaptação | rejeitada |

## Consequências

- **Positivas:** ciclo de aprendizado real, ligado a Memória/User Model/Eventos/Decisão;
  base para calibrar decisões pelo histórico (futuro).
- **Custos:** uma tabela + migração.
- **Neutras:** 2 tools + router `/api/v1/learning`.

## Riscos e mitigação

- **Risco:** avaliação de qualidade hoje é fornecida (dono/tool), não inferida →
  **Mitigação:** contrato estável; um avaliador (heurístico ou LLM local) pode ser plugado
  depois sem mudar chamadores.
- **Ponto de reversão:** remover tools/router; a tabela `learnings` cai via `downgrade`.

## Notas de implementação

`models.Learning`, `app/learning/service.py`, migração `bfb68861ee5d`,
`app/api/routers/learning.py`, tools em `brain/tools.py`, wiring em `core/di.py`, testes
`tests/test_learning.py`. CI verde: ruff + alembic + pytest (82 passed).
