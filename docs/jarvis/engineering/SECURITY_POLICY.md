# Política de Segurança — Sistema Imunológico Digital

> A segurança do JARVIS não é uma camada; é o **sistema imunológico** de um cérebro que é
> "só meu". Deriva da Constituição (Artigo VIII, princípio "só meu") e de
> `ARCHITECTURAL_PRINCIPLES.md` (security-by-design, privacy-by-design). Estado:
> `[PARCIAL]` — cofre criptografado, escopo de dono, capacidades sem URL arbitrária e
> pareamento de dispositivos já existem; o programa completo abaixo é o alvo.

## Princípio soberano: "só meu"

Todo o resto deriva daqui. **Um único dono. Nenhum dado sai sem escolha explícita do dono.
Nenhuma outra IA/LLM na nuvem tem acesso à cognição.** Segurança existe para tornar essa
promessa verdadeira na prática, não só no discurso.

## Zero Trust

Nada é confiável por padrão — nem dispositivos, nem agentes, nem capacidades, nem eventos.

- **Todo dispositivo é pareado** e autenticado (tokens de dono e de dispositivo; senhas com
  Argon2). Um dispositivo não pareado não fala com o Kernel.
- **Todo agente é escopado ao dono** e recebe o **menor privilégio** (toolset restrito por
  padrão — ver `../architecture/AGENT_SYSTEM.md`).
- **Todo evento de dispositivo é autenticado**; nenhum evento não confiável altera o World
  Model sem validação (ver `../architecture/EVENT_ARCHITECTURE.md`).
- **Toda capacidade** valida entrada, tem timeout e limite de tamanho de resposta.

## Criptografia

- **Segredos em repouso:** chaves/tokens de conector no cofre **Fernet**; nunca retornados,
  nunca logados.
- **Dados sensíveis em repouso** (memória pessoal, World Model, saúde/localização
  inferidas) criptografados.
- **Sincronização entre corpos** ocorre pela rede privada do dono (local/túnel), nunca por
  nuvem pública; canal autenticado e cifrado.
- **Chaves** são geridas localmente; a perda/rotação de chave é um procedimento documentado,
  não um improviso.

## Contenção do modelo e das ferramentas (o maior risco: prompt injection)

O LLM é poderoso e **falível**; tratamos toda saída do modelo como não confiável.

- **Sem URL/ação arbitrária a partir do modelo.** O modelo só invoca **capacidades
  definidas pelo dono, por nome** — o que impede que injeção de prompt vire SSRF ou execução
  arbitrária (ver `../architecture/API_ECOSYSTEM.md`).
- **O Kernel nunca executa ferramenta diretamente**; tudo passa pelo Tool Dispatcher, com
  validação de resultado.
- **Confirmação para efeitos irreversíveis** (apagar, gastar, enviar, abrir fechadura).
- **Sub-agentes sem recursão descontrolada** e com toolset restrito.

## Sandbox e isolamento

- Componentes de execução (automações, agentes, conectores) rodam com **privilégio mínimo**
  e isolados do núcleo cognitivo.
- Uma capacidade comprometida não deve alcançar o cofre, a memória bruta nem outros
  dispositivos além do seu escopo.
- Automações do n8n executam como **motor sem autoridade cognitiva** (ver
  `../agents/N8N_ORCHESTRATOR.md`), num ambiente contido.

## Segurança da cadeia de suprimentos (supply chain)

- **Dependências fixadas** e revisadas; nada de dependência não justificada (ver
  `../constitution/DECISION_PROCESS.md`).
- Adição de dependência de terceiros é uma decisão consciente, preferindo o que é auditável
  e mantido; dependências de rede/telemetria oculta são rejeitadas.
- Build reprodutível na medida do possível; artefatos de build não são confiados cegamente.

## Detecção de anomalias (o sistema imune ativo)

- Políticas de segurança **assinam eventos** e observam padrões anômalos (acesso incomum,
  volume estranho, dispositivo novo, tentativa de exfiltração).
- Toda ação sensível é **auditável**: existe trilha de quem/o quê/quando/por quê.
- Anomalia relevante **notifica o dono** e, conforme a política, contém antes de perguntar.

## Privacidade operacional

- **Dados pessoais nunca em git** (ver `DOCUMENTATION_RULES.md`): nada de memória real,
  segredo, token, localização ou identidade do dono em arquivos versionados.
- **Segredos nunca em código nem em log.**
- O dono pode **inspecionar, editar e esquecer** qualquer dado (curadoria soberana — ver
  `../architecture/MEMORY_ARCHITECTURE.md`).

## Resposta a incidentes

- Chave vazada → rotação imediata pelo procedimento documentado; segredos afetados
  reemitidos.
- Dispositivo perdido → revogação do token daquele corpo; a mente permanece intacta.
- Componente comprometido → isolar, revogar privilégio, auditar trilha, restaurar de estado
  bom conhecido.

## Não-objetivos

- Não somos um antivírus genérico nem um SOC corporativo; somos o sistema imune de **um**
  cérebro pessoal.
- Segurança **nunca** é usada como desculpa para enviar cognição/dados a serviços externos.
  A resposta segura, em caso de dúvida, é **manter local**.
