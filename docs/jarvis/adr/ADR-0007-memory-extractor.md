# ADR-0007: Extrator de Memória — auto-aprendizado tipado e multi-fato

> **Architecture Decision Record.** Evolui o auto-aprendizado da cognição de um fato único
> para extração estruturada, roteada para o grafo de memória e para o User Model. Conceito
> adaptado do OpenJarvis (Apache-2.0). Ver ADR-0001, ADR-0005 e
> `../architecture/MEMORY_ARCHITECTURE.md`.

- **Número:** 0007
- **Título:** MemoryExtractor — destilar vários fatos tipados por conversa
- **Data:** 2026-07-19
- **Estado:** `Aceito`
- **Autor(es):** Claude Code (Principal Engineer)
- **Aprovado por:** Proprietário ("extrator de memória")
- **Documentos afetados:** `../architecture/MEMORY_ARCHITECTURE.md`, `../architecture/WORLD_MODEL.md`

## Contexto

O `_auto_learn` da cognição destilava **um** fato por troca, sempre `kind="fact"`, sem rotear
traços do dono para o User Model. O `memory/extractor` do OpenJarvis (Apache-2.0) mostra o
design melhor: extração estruturada de múltiplos fatos classificados.

## Problema

Como extrair **vários** fatos duráveis e tipados por conversa, roteando cada um para o lugar
certo (grafo de memória vs. User Model), sem confiar cegamente na saída do modelo e sem
jamais quebrar a resposta ao dono?

## Decisão

Reimplementar o conceito como `MemoryExtractor` (`app/brain/extractor.py`):

- O **cérebro local** propõe candidatos como um array JSON:
  `{fato, tipo, importancia, chave_perfil?}`.
- Todo o resto é **determinístico e defensivo**: parse tolera cercas de markdown e prosa;
  saída malformada extrai nada; `tipo` é restringido a uma whitelist
  (`fact|preference|person|routine|note`); `importancia` é clampada a 0..1; no máximo
  **5 fatos** por troca; duplicatas exatas são puladas.
- **Roteamento:** todo fato vai ao grafo de **Memória** (auto-link, ADR da memória); um item
  com `chave_perfil` também vira atributo do **User Model** (ADR-0001), rotulado como
  **inferência**.
- **Auditável:** emite `memoria.extraida` (EventBus, ADR-0002) quando algo foi aprendido.
- A cognição usa o extrator dentro do mesmo contrato best-effort do `_auto_learn`: uma falha
  do extrator **nunca** quebra a resposta; sem extrator, o probe antigo continua como
  fallback. A flag `MEMORY_AUTO_LEARN` segue governando tudo.

Preserva os invioláveis: **"só meu"** (inferência 100% local via Ollama; nada sai), **Kernel
independente do modelo** (o LLM só propõe; validação/roteamento são determinísticos),
**substituibilidade** (contrato `extract()` estável).

### Atribuição (Apache-2.0)

Conceito adaptado do extrator de memória do **OpenJarvis** (open-jarvis/OpenJarvis,
Apache-2.0). Nenhum arquivo foi copiado; reimplementação própria, com crédito aqui e no
docstring do módulo.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| **Extração JSON tipada + validação determinística (escolhida)** | multi-fato, roteada, defensiva, testável | prompt maior por troca | — |
| Manter o probe de fato único | já existia | um fato por troca, sem tipos, sem User Model | mantido só como fallback |
| Copiar `memory/extractor.py` do OpenJarvis | rápido | arrasta abstrações deles; superfície não revisada | rejeitada |
| Extrair com regras/regex sem LLM | 100% determinístico | não entende linguagem natural; perderia quase tudo | rejeitada |

## Consequências

- **Positivas:** o segundo cérebro aprende mais e melhor por conversa; o User Model passa a
  ser alimentado automaticamente; extração auditável por eventos.
- **Custos:** uma chamada de inferência local um pouco maior por troca (max_tokens 400).
- **Neutras:** sem migração — escreve nas tabelas existentes.

## Riscos e mitigação

- **Risco:** o modelo inventar fatos → **Mitigação:** whitelist de tipos, corte de fatos
  curtos, dedupe, importância clampada; e a curadoria soberana do dono
  (inspecionar/editar/esquecer) vale para tudo que entra.
- **Ponto de reversão:** desligar `MEMORY_AUTO_LEARN` ou não injetar o extrator no DI — o
  fallback antigo volta sozinho.

## Notas de implementação

`app/brain/extractor.py`, integração em `brain/cognition.py` (`_auto_learn`), wiring em
`core/di.py`, testes `tests/test_extractor.py`. Sem migração. CI verde: ruff + alembic +
pytest (96 passed).
