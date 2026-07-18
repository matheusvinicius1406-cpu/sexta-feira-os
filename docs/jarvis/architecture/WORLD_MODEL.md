# World Model

> Como o JARVIS representa a **realidade atual**. Deriva da Constituição (Artigo V) e do
> `NORTH_STAR.md`. Estado: `[PARCIAL]` — o estado explícito existe (ver **ADR-0001**):
> armazenamentos tipados `WorldFact` (o presente) e `UserAttribute` (o dono), escopados ao
> dono, injetados na cognição a cada turno via `context_digest`, e curáveis em
> `/api/v1/world`. Ainda `[FUTURO]`: atualização por **eventos** e sincronização
> **distribuída** entre corpos (próximas etapas).

## O que é

O **World Model** é o estado interno vivo que o Kernel mantém **permanentemente** e
consulta em **toda** decisão. Ele responde: *"qual é a situação agora?"*. Junto com o
**User Model**, garante que **nenhuma solicitação começa do zero**.

Distinção: a **Memória Persistente** guarda o passado (o que aconteceu/foi aprendido); o
**World Model** guarda o presente (o que é verdade agora). O presente, ao passar, vira
memória episódica/temporal.

## Componentes do World Model (o presente)

- **Ambiente:** localização, horário, clima, dispositivos conectados, pessoas presentes.
- **Estado do usuário:** energia/humor inferidos, disponibilidade, foco atual.
- **Trabalho ativo:** projetos ativos, documentos abertos, tarefas em execução.
- **Objetivos atuais:** metas em andamento e sua prioridade.
- **Contexto recente:** últimas interações e decisões.
- **Capacidades disponíveis:** quais ferramentas/APIs/dispositivos estão online agora.

## User Model (o proprietário, ao longo do tempo)

Modelo persistente e evolutivo do dono, alimentado pela memória:
- objetivos, hábitos, preferências;
- forma de estudar, estilo de programação, padrões de escrita;
- conhecimentos adquiridos e dificuldades recorrentes;
- interesses, relações sociais relevantes, projetos pessoais;
- evolução ao longo dos anos.

Finalidade: **compreender profundamente** o dono para antecipar necessidades e
personalizar decisões — sempre sob "só meu".

## Como é mantido

O World Model é **atualizado por eventos** (ver `EVENT_ARCHITECTURE.md`): "usuário
acordou", "localização mudou", "documento aberto", "projeto compilado", "mensagem
recebida", "sensor ativado". Cada evento atualiza o estado; o Kernel nunca consulta um
mundo desatualizado.

```
Evento → normalização → atualização do World Model → (se relevante) memória episódica/temporal
```

## Como é usado

Em toda decisão, o **Context Manager** do Kernel injeta o recorte relevante do World Model
e do User Model no raciocínio. Exemplos:
- "abra meu projeto" resolve *qual* projeto pelo trabalho ativo + User Model;
- um lembrete considera localização e agenda atuais;
- uma sugestão respeita energia/foco inferidos.

## Contratos e invariantes

1. O World Model é **fonte única** do "agora"; componentes não mantêm cópias divergentes.
2. É **consultável** e **auditável**: dá para inspecionar o estado que embasou uma decisão.
3. É **substituível** na implementação (estrutura de dados/armazenamento trocáveis) atrás
   de um contrato estável.
4. Distribuído: o mesmo World Model lógico é compartilhado entre dispositivos via eventos.
5. Inferências (humor, energia) são **rotuladas como inferência**, com incerteza, nunca
   como fato definitivo.

## Privacidade

O World Model contém dados sensíveis do presente (localização, pessoas, saúde inferida).
Aplica-se "só meu": permanece local, criptografado quando sensível, e nunca é exposto a
terceiros sem escolha explícita do dono.
