# Regras de Documentação

> Como a documentação do JARVIS permanece verdadeira, consistente e útil para qualquer IA ou
> humano que chegue depois. Deriva de `ARCHITECTURAL_PRINCIPLES.md` (contratos, honestidade)
> e do `../constitution/AI_AGENT_RULES.md`. Estado: `[ATUAL]`.

## Por que estas regras existem

O pecado do projeto original foi **documentação aspiracional desconectada da realidade** —
docs descrevendo um sistema que não existia. Estas regras impedem a reincidência: a
documentação é uma **fonte de verdade**, não um folheto de marketing.

## Regra de ouro: honestidade de estado

Todo documento de arquitetura marca o estado do que descreve:

- `[ATUAL]` — existe e funciona no código hoje.
- `[PARCIAL]` — parte existe; o resto é evolução declarada.
- `[FUTURO]` — ainda não existe; é alvo de projeto.

**Nunca** descreva `[FUTURO]` como se fosse `[ATUAL]`. Se a realidade e o documento
divergirem, o documento está errado até ser corrigido.

## Hierarquia e precedência

A documentação segue a hierarquia de autoridade (ver `../README.md` e a Constituição):

```
Dono  >  Constituição  >  ADRs  >  Arquitetura  >  Engenharia / Agentes
```

Em conflito, o nível mais alto vence. Um documento nunca contradiz um nível acima dele; se
precisar, **emenda-se o nível acima** (Constituição via processo de emenda; decisões via
ADR).

## Consistência entre documentos

- **Vocabulário canônico único.** JARVIS OS = Sistema Operacional Cognitivo Pessoal (PCOS),
  **não** um chatbot/wrapper. Sexta-Feira = codinome da implementação atual. Kernel
  Cognitivo, World Model, Memória Persistente, Diretores, Capacidades, Tool Dispatcher,
  Barramento de Eventos — os nomes são estáveis e usados igualmente em todos os docs.
- **Fios de consistência inegociáveis:** "só meu" (dono único, privacidade total, nada de
  LLM na nuvem); o Kernel é **independente do modelo** (LLM substituível); hierarquia de
  autoridade (Dono → Kernel → Diretores/Agentes → Ferramentas/APIs/Dispositivos); nenhuma IA
  muda arquitetura sem ADR + aprovação do dono; n8n sem autoridade cognitiva; orientado a
  eventos.
- **Ligações cruzadas** entre documentos usam caminhos relativos e devem apontar para
  arquivos existentes.

## Idioma e forma

- **Português**, para casar com a base documental existente do projeto.
- Cada documento abre com um bloco `>` que diz **o que é**, **de onde deriva** e o **estado**.
- Direto e específico. Sem enrolação, sem promessa vaga.

## O que NUNCA entra na documentação (nem em qualquer arquivo versionado)

- **Dados pessoais do dono:** memórias reais, mensagens, localização, saúde, contatos.
- **Segredos:** chaves, tokens, senhas, hostnames internos.
- **Identificadores de modelo de IA** em artefatos do repositório (ficam só no chat).

## Quando criar/alterar documentação

- **Decisão arquitetural** → primeiro um ADR (`../adr/ADR_TEMPLATE.md`); depois os
  documentos de arquitetura afetados são atualizados para refletir a decisão.
- **Mudança de implementação** que altera um estado `[FUTURO]→[ATUAL]` → atualize o marcador
  no documento correspondente no mesmo PR.
- **Novo componente** → documente o contrato antes/junto do código (ver
  `CODING_STANDARDS.md`).

## Auditoria da própria documentação

A base documental é auditada de forma cruzada em `../../DOCUMENTATION_AUDIT.md`: contradições,
conflitos de autoridade, e a pergunta-chave — *uma IA nova conseguiria entender o sistema só
por estes arquivos?* A resposta precisa continuar sendo "sim".
