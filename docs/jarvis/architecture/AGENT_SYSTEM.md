# Sistema de Agentes

> Como o JARVIS delega trabalho a especialistas. Deriva da Constituição (Artigos IV, V).
> Estado: `[PARCIAL]` — sub-agentes temporários **e** Diretores permanentes existem (ver
> **ADR-0008**): gabinete canônico semeado por dono, memória especializada no substrato do
> grafo (`source='director:<nome>'`), delegação com toolset restrito, consolidação de
> aprendizado no diretor, recursão bloqueada, eventos auditáveis; exposto em
> `/api/v1/directors` e pela tool `consult_director`. Ainda `[FUTURO]`: diretores criando
> agentes temporários próprios e recall semântico da expertise.

## Princípio de autoridade

O **JARVIS (via Cognitive Kernel) possui autoridade total** sobre os agentes. Todos os
demais agentes são **subordinados**. Nenhum agente age no mundo real sem autorização do
Kernel. Nenhum agente altera arquitetura (isso é do `DECISION_PROCESS.md`).

```
Cognitive Kernel
   ↓  delega
Directors (agentes permanentes, especialistas de domínio)
   ↓  criam sob demanda
Agentes temporários (tarefas específicas)
   ↓  usam
Tools / APIs / Devices
```

## Tipos de agente

### Agentes permanentes — "Diretores"
Especialistas de domínio, com **memória especializada** própria (sob o mesmo substrato e
políticas da Memória Persistente). Persistem ao longo do tempo e acumulam expertise.

Exemplos de Diretores:
- Diretor de Engenharia
- Diretor de Segurança
- Diretor de Pesquisa
- Diretor de Memória
- Diretor de Automação
- Diretor de Aprendizagem
- Diretor de Dispositivos
- (conforme necessidade do dono) Diretor Financeiro, Médico, Jurídico — sempre com a
  ressalva ética/legal: informam e auxiliam, **não substituem** profissionais.

### Agentes temporários
Criados por um Diretor (ou pelo Kernel) para uma tarefa específica; encerrados ao concluir.
O **aprendizado permanece no Diretor responsável**, não no agente temporário.

Exemplo:
```
Diretor de Engenharia
   ↓ cria
Backend Agent · Android Agent · DevOps Agent · Database Agent · Testing Agent · Doc Agent
```
Ao concluir: consolidam conhecimento no Diretor, retornam resultados, podem ser encerrados.

## Regras de segurança dos agentes

1. **Toolset restrito por padrão.** Sub-agentes recebem apenas as ferramentas necessárias.
   Por padrão, **consultam/pesquisam** (leitura); ações irreversíveis ou externas ficam com
   o Kernel/Diretor autorizado.
2. **Sem recursão descontrolada.** Um agente temporário não delega adiante além do limite
   definido; evita-se spawn infinito.
3. **Owner-scoped.** Todo agente opera sob o único dono; nunca cruza fronteiras de "só meu".
4. **Local e privado.** Agentes rodam sobre o modelo local; nenhuma cognição vaza para a
   nuvem.
5. **Auditável.** Cada delegação e resultado é registrado.

## Comunicação entre agentes

- Preferencialmente por **eventos** e por **resultados consolidados** devolvidos ao
  solicitante, não por acoplamento direto.
- O Kernel é o **árbitro**: consolida resultados divergentes, resolve conflitos, decide.
- Diretores expõem **contratos** (o que sabem fazer, entradas/saídas); o Kernel escolhe a
  quem delegar.

## Memória especializada

Cada Diretor mantém memória do seu domínio (ex.: o Diretor de Engenharia lembra decisões
técnicas, padrões, bugs recorrentes). Essa memória:
- usa o mesmo substrato de grafo (`MEMORY_ARCHITECTURE.md`);
- é consultável pelo Kernel;
- respeita as mesmas políticas de privacidade e auditoria.

## Relação com as IAs de desenvolvimento

As IAs que **constroem** o JARVIS (Claude Code, Gemini, Hermes, Copilot) têm contratos em
`agents/`. Elas não são os agentes *de runtime* do JARVIS, mas seguem a mesma filosofia de
papéis, limites e subordinação ao processo de decisão. Um Diretor de runtime pode, no
futuro, ser materializado a partir dessas ferramentas — sempre via ADR.
