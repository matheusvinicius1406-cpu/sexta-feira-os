# Princípios Arquiteturais do JARVIS OS

> Deriva de `JARVIS_CONSTITUTION.md`. Define **como** o sistema deve ser desenhado em
> qualquer camada. Toda decisão técnica é avaliada contra estes princípios.

## 1. Modularidade

Cada subsistema (Kernel, Memória, World Model, Planejamento, etc.) e cada capacidade
(API, ferramenta, dispositivo, agente) é um **módulo com contrato explícito**. Módulos se
comunicam por interfaces estáveis, nunca por acoplamento a implementações internas.
Objetivo: partes evoluem e são substituídas isoladamente, sem reescrever o todo.

## 2. Substituição de componentes (Replaceability)

Nenhum componente é "para sempre". Em especial:
- **O modelo de IA é substituível** sem perda de identidade, memória ou aprendizado.
- APIs, ferramentas, o motor de automação (n8n hoje), o banco de dados e até camadas
  inteiras podem ser trocados desde que respeitem o contrato do módulo.
Regra prática: dependa de **interfaces/portas**, não de fornecedores concretos.

## 3. Domínio separado da implementação (Ports & Adapters / Hexagonal)

A **lógica cognitiva** (domínio: o que decidir, lembrar, planejar) é separada da
**implementação técnica** (adaptadores: qual banco, qual LLM, qual HTTP). O domínio não
conhece detalhes de infraestrutura. Adaptadores são plugáveis. Isso protege o núcleo de
mudanças tecnológicas.

## 4. Arquitetura Orientada a Eventos (Event-Driven)

O sistema reage a **eventos** (ver `architecture/EVENT_ARCHITECTURE.md`). Componentes
publicam e assinam eventos em vez de se chamarem diretamente quando o acoplamento
temporal não é necessário. Benefícios: desacoplamento, extensibilidade, presença
distribuída, auditabilidade natural do fluxo.

## 5. Segurança por Design (Security by Design)

Segurança não é uma etapa final; é premissa de cada módulo: Zero Trust, menor privilégio,
isolamento, criptografia, validação de entrada, assinatura de artefatos. Ver
`engineering/SECURITY_POLICY.md`. Um design que só é seguro "se configurado corretamente"
é considerado inseguro.

## 6. Privacidade por Design ("só meu")

Dados pessoais permanecem sob controle do proprietário. Local-first por padrão; qualquer
saída de dados é uma **escolha explícita** por capacidade, nunca um efeito colateral.
Segredos criptografados em repouso. Sem telemetria.

## 7. Offline-First quando aplicável

Capacidades essenciais (raciocínio local, memória, agendamento) devem funcionar **sem
internet**. Recursos que exigem rede degradam com clareza (falha explícita), nunca
comprometem o núcleo. A presença de um serviço externo indisponível não derruba o Kernel.

## 8. Escalabilidade (para um dono, por décadas)

A escala do JARVIS não é "muitos usuários", e sim **muito tempo, muita memória, muitas
capacidades e muitos dispositivos** para uma pessoa. O design deve suportar crescimento de
memória (anos de dados), do catálogo de capacidades (milhares) e da malha de dispositivos —
com estruturas indexáveis e substituíveis (ex.: índice vetorial trocável).

## 9. Observabilidade

Todo subsistema é observável: logs estruturados, métricas, rastros de decisão e trilha de
auditoria. É preciso poder responder "por que o JARVIS fez X?" a qualquer momento. Sem
observabilidade, não há confiança nem evolução segura.

## 10. Determinismo e Reprodutibilidade onde importa

Fluxos de dados, migrações e pipelines de evolução devem ser reprodutíveis e versionados.
O comportamento do LLM é probabilístico, mas o **arcabouço** ao redor dele (memória,
despacho de ferramentas, políticas) é determinístico e testável.

## 11. Degradação graciosa

Falha de um componente (modelo offline, API fora, dispositivo desconectado) resulta em
resposta clara e segura, nunca em corrupção de estado. O padrão do projeto: erro explícito
(ex.: 503) em vez de comportamento silencioso incorreto.

## 12. Contratos antes de código

Cada módulo novo começa por seu **contrato** (entradas, saídas, invariantes, eventos)
documentado. Implementação vem depois. Contratos mudam via `DECISION_PROCESS.md`.

---

### Tensões conhecidas (e como resolvê-las)

- **Offline-first × capacidades de nuvem:** o núcleo é offline; capacidades de rede são
  módulos opcionais que degradam. Nunca o inverso.
- **Autoevolução × segurança:** toda autoevolução passa pelo pipeline de sandbox/auditoria
  (Constituição, Artigo VI). Velocidade nunca justifica pular a auditoria.
- **Modularidade × desempenho:** prefira clareza e contratos; otimize com medição
  (observabilidade), não por suposição.
