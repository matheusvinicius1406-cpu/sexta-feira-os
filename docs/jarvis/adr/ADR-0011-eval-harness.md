# ADR-0011: Eval Harness — o cérebro mede a própria qualidade

> **ADR.** Harness de avaliação local (conceito do OpenJarvis, Apache-2.0), ligado ao Learning
> Engine. Ver ADR-0002 (Eventos), ADR-0005 (Learning) e a Constituição (modelo substituível).

- **Número:** 0011 · **Data:** 2026-07-19 · **Estado:** `Aceito`
- **Autor:** Claude Code · **Aprovado por:** Proprietário ("faça logo tudo em sequência")

## Contexto e problema

A Constituição diz que o **modelo de IA é substituível** — mas não havia como **provar** que
uma troca de modelo não regrediu a qualidade. Faltava um harness de avaliação, e ele precisa
ser 100% local ("só meu"; o `evals/` do OpenJarvis tem backends de nuvem — descartados).

## Decisão

Modelos `EvalCase` (prompt + substring esperada) e `EvalRun` (score + resultados) e o serviço
`EvalHarness`: o dono define casos; o harness roda cada um no **cérebro local**, pontua
pass/fail de forma determinística (substring case-insensitive), persiste o run, publica
`avaliacao.executada` e **registra o score no Learning Engine** (`tag="eval"`) — uma queda de
qualidade vira uma lição registrada. Útil antes/depois de trocar o modelo local.

Atribuição: conceito do `evals/` do **OpenJarvis** (Apache-2.0); nenhum arquivo copiado,
reimplementação própria, sem backends de nuvem.

Preserva "só meu", Kernel independente do modelo (agora **auditável**) e substituibilidade.

## Consequências

- **Positivas:** dá para medir e comparar a qualidade do cérebro; troca de modelo deixa de ser
  fé; feed automático ao aprendizado.
- **Custos:** duas tabelas (migração compartilhada); N inferências locais por run.
- **Reversão:** remover router/wiring; tabelas caem via `downgrade`.

## Notas

`models.EvalCase/EvalRun`, `app/evals/service.py`, `app/api/routers/evals.py`, migração
`5a60d68e75fa`, testes `tests/test_life.py`. CI verde (115 passed).
