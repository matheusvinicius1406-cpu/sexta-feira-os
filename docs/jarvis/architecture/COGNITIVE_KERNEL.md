# Cognitive Kernel

> O núcleo absoluto do JARVIS OS. Deriva da Constituição (Artigos IV, V, VIII).
> Estado atual: `[PARCIAL]` — existe um loop cognitivo funcional; os motores dedicados
> abaixo são a evolução formal.

## Papel

O Kernel é o **único ponto de decisão** do sistema. Toda ação relevante passa por ele.
Nenhuma API, ferramenta, dispositivo ou agente executa algo sem sua autorização. O Kernel
é **independente do modelo de IA**: ele *usa* um LLM como mecanismo de raciocínio, mas sua
identidade, memória e políticas não dependem de qual modelo está ativo.

## Responsabilidades

- **Consciência do estado atual** — manter e consultar o World Model e o User Model.
- **Gestão de contexto** — montar o contexto certo para cada raciocínio (persona +
  memória recuperada + histórico + objetivo).
- **Memória** — orquestrar leitura/escrita na Memória Persistente.
- **Planejamento** — transformar objetivos em planos e subtarefas.
- **Tomada de decisão** — escolher entre alternativas sob restrições e políticas.
- **Priorização** — ordenar tarefas por importância, prazo, dependências, energia do dono.
- **Coordenação de agentes** — delegar a Diretores/sub-agentes e consolidar resultados.
- **Coordenação de APIs/ferramentas** — selecionar e despachar capacidades (nunca executar
  diretamente).
- **Segurança** — aplicar políticas do Sistema Imunológico Digital em cada decisão.
- **Aprendizado contínuo** — acionar o Learning Engine após cada ação.

## Componentes internos (contratos)

O Kernel é composto por motores modulares e substituíveis, cada um com contrato próprio:

| Componente | Função | Documento |
|---|---|---|
| **Context Manager** | monta o contexto de cada raciocínio | este |
| **World Model** | representação viva da realidade | `WORLD_MODEL.md` |
| **Memory Interface** | porta para a Memória Persistente | `MEMORY_ARCHITECTURE.md` |
| **Planning Engine** | objetivos → planos → subtarefas | este / futuro |
| **Reasoning (LLM adapter)** | mecanismo de raciocínio acionável e trocável | este |
| **Decision Engine** | escolha sob restrições e políticas | este / futuro |
| **Task Scheduler** | executar/pausar/repriorizar/reagendar | `EVENT_ARCHITECTURE.md` |
| **Tool Dispatcher** | selecionar, despachar, validar, registrar ferramentas | `API_ECOSYSTEM.md` |
| **Sub-Agent Coordinator** | delegar a agentes e consolidar | `AGENT_SYSTEM.md` |
| **Security Guard** | aplicar Zero Trust e políticas | `../engineering/SECURITY_POLICY.md` |
| **Learning Hook** | registrar aprendizado pós-ação | este / futuro |

O **Reasoning (LLM adapter)** é a única parte ligada a um modelo, e é um adaptador: trocar
o modelo troca só este adaptador, preservando todo o resto.

## Fluxo interno (loop cognitivo)

```
Evento ou solicitação
   ↓
Context Manager  (World Model + User Model + memória recuperada + histórico)
   ↓
Planning Engine  (objetivo → plano → subtarefas)
   ↓
Reasoning        (LLM raciocina sobre o plano/contexto)
   ↓
Decision Engine  (escolhe ação sob políticas/segurança)
   ↓
Task Scheduler   (agenda/prioriza a execução)
   ↓
Tool Dispatcher / Sub-Agent Coordinator  (despacha capacidade ou delega)
   ↓
Validação → Registro (auditoria)
   ↓
Learning Hook    (observa resultado → atualiza memória e comportamento)
```

Princípio: **nenhuma solicitação começa "do zero"** — o contexto sempre inclui o estado
cognitivo atual.

## Autoridade

- **Operacional (runtime):** o Kernel é soberano — coordena agentes, seleciona
  ferramentas, decide e prioriza.
- **Arquitetural:** o Kernel **não** tem autoridade — mudanças estruturais seguem o
  `DECISION_PROCESS.md` e a aprovação do proprietário.
- **Sobre o próprio núcleo:** o Kernel **nunca** se modifica diretamente; evolução do
  núcleo passa pelo pipeline auditado (Constituição, Artigo VI).

## Comunicação

- Para dentro: chama seus motores por interfaces (contratos), nunca por implementações.
- Para fora: publica e assina **eventos** (ver `EVENT_ARCHITECTURE.md`); despacha
  ferramentas pelo Tool Dispatcher; delega a agentes pelo Coordinator.
- Distribuído: o mesmo estado cognitivo é compartilhado entre dispositivos via eventos, de
  modo que qualquer "corpo" fala com o mesmo Kernel lógico.

## Invariantes (não violar)

1. Toda ação relevante é autorizada pelo Kernel.
2. O modelo de IA é acessado só pelo adaptador de Reasoning.
3. Toda decisão considera o World Model/User Model.
4. Toda ação relevante é registrada de forma auditável.
5. Ações irreversíveis exigem confirmação explícita.
