# North Star — Visão Arquitetural do JARVIS OS

> O destino de longo prazo. Este documento é o **alvo** que orienta toda decisão. Ele é
> intencionalmente ambicioso (décadas). Marcadores `[ATUAL] / [PARCIAL] / [FUTURO]`
> indicam o estado presente na implementação Sexta-Feira, para ancorar visão à realidade.

## Objetivo final

Evoluir, ao longo dos anos, de um assistente local para uma **entidade computacional
persistente** — um **Sistema Operacional Cognitivo Evolutivo** cuja *inteligência* reside
no Cognitive Kernel, cuja *experiência* reside na Memória Persistente, e cuja *capacidade
de ação* emerge de um ecossistema modular de agentes, ferramentas, APIs e dispositivos —
crescendo continuamente junto ao seu único proprietário durante toda a vida.

## Visão de longo prazo (a entidade que queremos)

Um JARVIS que:
- aprende continuamente e lembra permanentemente;
- compreende profundamente o proprietário e antecipa necessidades;
- coordena milhares de ferramentas e múltiplos dispositivos como um só;
- cria novos agentes especializados e novas capacidades quando preciso;
- protege a própria infraestrutura (Sistema Imunológico Digital);
- auxilia em praticamente qualquer atividade intelectual ou operacional — sempre sob
  controle e propriedade exclusivos do dono.

## Arquitetura conceitual

```
Sensores → Drivers → Cognitive Kernel → Persistent Memory → Planning →
Reasoning → Decision Engine → Task Scheduler → Tool Dispatcher →
Sub-Agent System → APIs / Ferramentas / Dispositivos
```

- **Cognitive Kernel** [PARCIAL] — núcleo de decisão. Hoje: loop cognitivo com
  tool-calling, persona, memória injetada.
- **Persistent Memory** [PARCIAL] — memória multi-categoria. Hoje: grafo de conhecimento
  persistente (episódica/semântica via nós + relações nomeadas); demais categorias
  formalizadas em `MEMORY_ARCHITECTURE.md` como evolução.
- **World Model** [FUTURO] — estado vivo da realidade (ver `WORLD_MODEL.md`). Hoje:
  implícito no histórico/contexto; a ser tornado explícito.
- **Planning / Decision / Learning Engines** [PARCIAL] — hoje: auto-aprendizado de fatos e
  agendamento; motores formais de planejamento/decisão são evolução.
- **Task Scheduler** [ATUAL] — agendador de lembretes e ações no tempo.
- **Tool Dispatcher / Sub-Agent System** [ATUAL] — despacho de ferramentas e sub-agentes
  locais com toolset restrito.
- **APIs / Ferramentas / Dispositivos** [ATUAL] — conectores de API (chaves
  criptografadas), automações n8n, protocolo de ação para dispositivos.

## Pilares que nunca mudam

1. **Persistência cognitiva** — nunca reinicia identidade; toda interação altera o estado.
2. **O LLM é substituível** — identidade/memória/aprendizado vivem no Kernel, não no modelo.
3. **Kernel soberano na execução** — nenhuma capacidade age sem sua autorização.
4. **"Só meu"** — local-first, privado, dono único.
5. **Evolução segura** — autoevolução por pipeline auditado; o Kernel nunca reescreve o
   próprio núcleo diretamente.

## Estado cognitivo permanente

O Kernel mantém sempre um **World Model** (realidade atual: localização, horário, agenda,
dispositivos, projetos, objetivos, contexto recente, histórico de decisões) e um **User
Model** (objetivos, hábitos, preferências, estilo, conhecimento, relações, evolução ao
longo dos anos). **Nenhuma solicitação começa do zero**: toda decisão considera esse
estado. (Detalhes em `WORLD_MODEL.md`.)

## Autoevolução

O sistema pode criar ferramentas, APIs, automações e agentes, escrever código, gerar
documentação, testar e pesquisar novas tecnologias — sempre pelo pipeline:
`Pesquisa → Sandbox → Testes → Benchmarks → Validação → Auditoria → Implantação`. O núcleo
nunca é alterado diretamente (Constituição, Artigo VI).

## Presença distribuída

Um único estado cognitivo, muitos corpos: smartphone, notebook, desktop, smartwatch,
smart ring, veículos, robôs, servidores, óculos, IoT, ESP32, Raspberry Pi. Todos
compartilham a mesma mente via eventos (ver `EVENT_ARCHITECTURE.md` e o ecossistema de
dispositivos).

## Evolução esperada (fases, não prazos)

1. **Fundação** [ATUAL] — kernel local, memória-grafo, ferramentas, ação, agenda,
   conectores, sub-agentes; CI, migrações, segurança básica.
2. **Corpos** — agentes nativos (Android/Desktop) executando de fato; presença ambiente.
3. **Cognição explícita** — World Model e User Model formais; motores de planejamento,
   decisão e aprendizado dedicados.
4. **Diretores** — sistema de agentes permanentes especializados com memória própria.
5. **Imunidade** — Sistema Imunológico Digital completo.
6. **Autoevolução** — pipeline de autoaperfeiçoamento em sandbox, auditado.
7. **Entidade persistente** — o PCOS evolutivo pleno.

Cada fase avança apenas quando a anterior está sólida, testada e auditada.
