# JARVIS OS — Base Documental Oficial (Governança Arquitetural)

> Esta pasta é a **fonte oficial de verdade** que governa todo o desenvolvimento do
> JARVIS OS. Toda IA participante do projeto — Claude Code, Gemini, Hermes, Copilot e
> qualquer agente criado pelo próprio JARVIS — DEVE ler e obedecer estes documentos
> antes de propor ou executar qualquer mudança.

## O que é o JARVIS OS

O JARVIS OS é um **Sistema Operacional Cognitivo Pessoal (Personal Cognitive Operating
System — PCOS)**: um segundo cérebro digital com memória persistente, identidade
contínua, aprendizado ao longo da vida, planejamento, execução de tarefas, coordenação
de agentes e evolução contínua. **Não é** um chatbot, um assistente simples nem um
wrapper de LLM. O modelo de linguagem é um componente **substituível**; o sistema real é
o Cognitive Kernel + Memória Persistente + World Model + os motores e ecossistemas.

## Nota de realidade (visão × implementação)

- **JARVIS OS** é o nome arquitetural (o North Star, projetado para décadas).
- **Sexta-Feira** é o codinome da **implementação atual** (o kernel local já em produção
  neste repositório): memória-grafo, conectores de API, sub-agentes, protocolo de ação,
  agendador, automações n8n — tudo local, privado, dono único.
- Estes documentos descrevem o **alvo**. O que já existe é uma **realização parcial**.
  Cada documento de `architecture/` marca o que é `[ATUAL]`, `[PARCIAL]` ou `[FUTURO]`
  para que nenhuma IA confunda projeto com estado presente.

## Estrutura

```
docs/jarvis/
├── constitution/     # A lei suprema: identidade, princípios, autoridade, processo
│   ├── JARVIS_CONSTITUTION.md
│   ├── ARCHITECTURAL_PRINCIPLES.md
│   ├── AI_AGENT_RULES.md
│   └── DECISION_PROCESS.md
├── architecture/     # O desenho conceitual do sistema
│   ├── NORTH_STAR.md
│   ├── COGNITIVE_KERNEL.md
│   ├── MEMORY_ARCHITECTURE.md
│   ├── WORLD_MODEL.md
│   ├── AGENT_SYSTEM.md
│   ├── API_ECOSYSTEM.md
│   └── EVENT_ARCHITECTURE.md
├── engineering/      # Como construímos (padrões operacionais)
│   ├── CODING_STANDARDS.md
│   ├── GIT_WORKFLOW.md
│   ├── TESTING_STRATEGY.md
│   ├── SECURITY_POLICY.md
│   └── DOCUMENTATION_RULES.md
├── agents/           # Contratos de cada IA participante
│   ├── CLAUDE_CODE.md
│   ├── GEMINI.md
│   ├── HERMES.md
│   ├── COPILOT.md
│   └── N8N_ORCHESTRATOR.md
├── adr/              # Registro de decisões arquiteturais
│   └── ADR_TEMPLATE.md
└── DOCUMENTATION_AUDIT.md   # Auditoria cruzada desta base documental
```

## Ordem de precedência (em caso de conflito)

1. **Vontade do proprietário** (o dono único do JARVIS).
2. `constitution/JARVIS_CONSTITUTION.md` (a lei suprema).
3. Demais documentos de `constitution/`.
4. ADRs aprovados (`adr/`), do mais recente que revoga o anterior.
5. Documentos de `architecture/`.
6. Documentos de `engineering/` e `agents/`.

Nenhum documento de nível inferior pode contradizer um superior. Se contradisser, o
inferior está errado e deve ser corrigido via `DECISION_PROCESS.md`.

## Versionamento

Esta base é versionada como `v1.0` (fundação). Mudanças seguem
`constitution/DECISION_PROCESS.md` — sempre via ADR e aprovação do proprietário.
