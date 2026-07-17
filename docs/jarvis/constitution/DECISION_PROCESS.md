# Processo de Decisão Arquitetural

> Como decisões importantes acontecem no JARVIS OS. Deriva da Constituição (Artigo VI).
> Nenhuma mudança arquitetural é legítima fora deste processo.

## Fluxo canônico

```
Problema
   ↓
Pesquisa
   ↓
Proposta
   ↓
ADR (registro formal)
   ↓
Aprovação (proprietário)
   ↓
Implementação
   ↓
Auditoria
```

Cada etapa produz um artefato rastreável. O ADR é o documento oficial da decisão.

## Etapas

### 1. Problema
Descreva o problema/necessidade de forma neutra: o que dói, o contexto, os sintomas.
Ainda **sem** solução. Registre quem levantou e por quê.

### 2. Pesquisa
Investigue alternativas com honestidade: prós, contras, custo, risco, impacto na
Constituição e nos princípios (`ARCHITECTURAL_PRINCIPLES.md`). É o papel natural do
**Gemini** (Research) e, em análise crítica, do **Hermes** (auditoria).

### 3. Proposta
Sintetize uma recomendação com base na pesquisa. A proposta aponta a alternativa
preferida **e** as descartadas, com justificativa (regra: nenhuma tecnologia escolhida
sem justificativa).

### 4. ADR (Architecture Decision Record)
Formalize no formato de `adr/ADR_TEMPLATE.md`. O ADR contém contexto, problema, decisão,
alternativas, consequências e riscos. ADRs são **imutáveis após aprovados**: uma decisão
nova que muda a anterior cria um **novo** ADR que a "supersede".

### 5. Aprovação
Somente o **proprietário** aprova mudanças arquiteturais (Constituição, Artigo VI). A
aprovação é registrada no ADR (status `Aceito`). Sem aprovação, nada é implementado.

### 6. Implementação
Executada pelas IAs de desenvolvimento (ex.: **Claude Code**) estritamente dentro do
escopo do ADR e dos padrões de `engineering/`. Mudança de comportamento exige teste que a
comprove.

### 7. Auditoria
Após implementar, verifica-se que o resultado corresponde ao ADR e não violou princípios.
Papel natural do **Hermes**. Divergências reabrem o processo (novo ADR ou correção).

## Quando um ADR é obrigatório

- Mudança em qualquer subsistema canônico (Constituição, Artigo VIII) ou seu contrato.
- Mudança na hierarquia de autoridade ou nas permissões de agentes.
- Mudança na postura de segurança ou privacidade.
- Introdução/troca de uma tecnologia estrutural (banco, motor de automação, protocolo,
  padrão de comunicação).
- Qualquer coisa que afete os Princípios Invioláveis.

## Quando um ADR **não** é necessário

- Correções de bug dentro de contratos existentes.
- Novas capacidades/ferramentas que respeitam contratos e padrões vigentes.
- Refatorações internas que preservam o contrato do módulo.

Nestes casos, segue-se `engineering/GIT_WORKFLOW.md` (PR + revisão), sem ADR.

## Estados de um ADR

`Proposto` → `Em revisão` → `Aceito` | `Rejeitado` → (futuro) `Supersedido por ADR-XXXX`.

## Emergências

Se uma ação urgente e reversível for necessária antes de um ADR (ex.: mitigar um
incidente de segurança), ela pode ser tomada **desde que**: seja reversível, seja
registrada imediatamente, e um ADR retroativo seja aberto em seguida para ratificá-la ou
revertê-la. Ações irreversíveis nunca se enquadram em "emergência".
