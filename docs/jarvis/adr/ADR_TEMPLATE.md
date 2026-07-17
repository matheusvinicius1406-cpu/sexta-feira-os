# ADR-NNNN: <título curto e imperativo da decisão>

> **Architecture Decision Record.** Uma decisão arquitetural do JARVIS é registrada aqui —
> nunca só num commit, num comentário ou na cabeça de alguém. Ver
> `../constitution/DECISION_PROCESS.md` (quando um ADR é exigido) e
> `../engineering/DOCUMENTATION_RULES.md`. Copie este arquivo para `ADR-NNNN-<slug>.md`,
> preencha e submeta à aprovação do **dono**.

- **Número:** NNNN (sequencial)
- **Título:** <o que se decide, em uma linha>
- **Data:** AAAA-MM-DD
- **Estado:** `Proposto` → `Aceito` / `Rejeitado` / `Substituído por ADR-XXXX`
- **Autor(es):** <IA/pessoa que propõe (ex.: Gemini como Research Engineer)>
- **Aprovado por:** <só o dono aprova uma decisão arquitetural>
- **Documentos afetados:** <lista de docs de arquitetura/engenharia que mudam com esta decisão>

## Contexto

Qual é a situação atual e as forças em jogo? O que é verdade hoje no sistema (`[ATUAL]`) que
torna esta decisão necessária? Sem contexto, ninguém no futuro entende o porquê.

## Problema

O que exatamente precisa ser decidido? Formule como uma pergunta única e clara. Se há mais de
uma decisão, provavelmente há mais de um ADR.

## Decisão

O que foi decidido, de forma inequívoca. Descreva a escolha e como ela se encaixa nos
contratos e na hierarquia de autoridade (Dono → Kernel → Diretores/Agentes →
Ferramentas/APIs/Dispositivos).

Marque explicitamente que a decisão **preserva os princípios invioláveis**:
- Mantém "só meu" (sem LLM na nuvem, sem exfiltração, sem dado pessoal em git)?
- Mantém o Kernel **independente do modelo** (LLM continua substituível)?
- Mantém a substituibilidade (o que se escolhe fica atrás de um contrato)?

## Alternativas consideradas

Liste as opções reais avaliadas e por que **não** foram escolhidas. Uma decisão sem
alternativas registradas é suspeita.

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Opção A (a escolhida) | … | … | — |
| Opção B | … | … | … |
| Opção C | … | … | … |

## Consequências

O que muda por causa desta decisão — o bom e o ruim.

- **Positivas:** o que passa a ser possível/melhor.
- **Negativas / custos:** o que fica mais difícil, que dívida se assume.
- **Neutras:** efeitos colaterais a registrar.

## Riscos e mitigação

- **Risco:** <o que pode dar errado> → **Mitigação:** <como reduzimos/monitoramos>.
- **Ponto de reversão:** como e a que custo esta decisão pode ser revertida ou substituída
  (por um ADR futuro) se provar errada.

## Justificativa de tecnologia (se aplicável)

Se a decisão escolhe uma tecnologia concreta, **justifique** (a Constituição proíbe escolher
tecnologia sem justificativa). Por que esta, e não as alternativas, à luz de "só meu",
substituibilidade e do perfil real do problema.

## Notas de implementação

Ligações para os documentos de arquitetura/engenharia atualizados e para o trabalho de
implementação que decorre desta decisão (sem incluir segredos, dados pessoais nem
identificadores de modelo — ver `../engineering/DOCUMENTATION_RULES.md`).
