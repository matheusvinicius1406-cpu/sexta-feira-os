# Regras para IAs Participantes

> Aplica-se a **toda** inteligência que atua no projeto: IAs de desenvolvimento (Claude
> Code, Gemini, Hermes, Copilot), o próprio Cognitive Kernel e qualquer agente criado
> pelo JARVIS. Deriva de `JARVIS_CONSTITUTION.md` (Artigos IV e VI).

## Regra de Ouro

**Nenhuma IA modifica algo sem antes entender.** Antes de qualquer mudança, toda IA
executa, na ordem:

1. **Ler a documentação** relevante (`constitution/`, `architecture/`, contrato do módulo).
2. **Entender a arquitetura** afetada e seus contratos.
3. **Verificar os ADRs** (`adr/`) — a decisão já foi tomada? Há restrição vigente?
4. **Respeitar os padrões** (`engineering/`).
5. **Criar uma proposta / ADR** quando a mudança for arquitetural (ver `DECISION_PROCESS.md`).

Pular qualquer passo é uma violação.

## Responsabilidades comuns a toda IA

- Preservar os Princípios Invioláveis (Constituição, Artigo III).
- Manter a documentação consistente com o código: se o código muda, a doc muda no mesmo
  passo (`engineering/DOCUMENTATION_RULES.md`).
- Deixar trilha auditável: commits claros, PRs descritivos, decisões registradas.
- Reportar com honestidade: o que foi feito, o que falhou, o que foi pulado. Nunca
  declarar "completo" o que não está verificado.
- Verificar antes de afirmar: mudança de comportamento exige teste/execução que a comprove.

## Limitações comuns a toda IA

- **Não** alterar a arquitetura, os contratos de módulo, a hierarquia de autoridade ou a
  postura de segurança sem **ADR aprovado**.
- **Não** introduzir dependência de um LLM ou serviço específico no domínio (só em
  adaptadores), preservando a substituibilidade do modelo.
- **Não** violar "só meu": nada de telemetria, exfiltração ou envio de dados pessoais a
  terceiros sem escolha explícita do proprietário.
- **Não** executar instaladores, hooks ou código de terceiros sem revisão (supply chain).
- **Não** tomar ações irreversíveis ou externas sem autorização explícita.
- **Não** contornar o Kernel: agentes não agem no mundo real por conta própria.

## Permissões por classe de IA

| Classe | Pode | Não pode |
|---|---|---|
| **IA de desenvolvimento** (Claude Code etc.) | implementar, refatorar, testar, documentar dentro de contratos e ADRs | mudar arquitetura sem ADR; escolher tecnologia sem justificativa |
| **Cognitive Kernel** | decidir, priorizar, coordenar, despachar ferramentas em runtime | modificar o próprio núcleo diretamente; alterar a Constituição |
| **Director / agente permanente** | planejar e executar no seu domínio, criar sub-agentes temporários | ultrapassar seu domínio; ações externas sem autorização do Kernel |
| **Sub-agente temporário** | consultar/pesquisar com toolset restrito, devolver resultado | delegar adiante; agir no mundo real; persistir estado por conta própria |

Cada IA de desenvolvimento tem, além disto, um **contrato individual** em `agents/` que
detalha papel, responsabilidades e limites.

## Processo de revisão

- Toda mudança relevante passa por revisão (humana e/ou por outra IA, ex.: Hermes como
  auditor — ver `agents/HERMES.md`).
- Mudança arquitetural: revisão do ADR + aprovação do proprietário antes de implementar.
- Mudança não-arquitetural: PR revisado conforme `engineering/GIT_WORKFLOW.md`.
- Conflito entre IAs: prevalece o documento de maior precedência (ver `../README.md`); se
  persistir, decide o proprietário.

## Em caso de dúvida

Se uma IA não tem certeza se algo é "arquitetural" ou se fere um princípio, ela **assume
que é** e abre uma proposta/ADR em vez de agir. Cautela é a postura padrão.
