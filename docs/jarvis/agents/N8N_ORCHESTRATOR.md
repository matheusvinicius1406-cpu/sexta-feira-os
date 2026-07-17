# n8n — Camada de Automação (sem autoridade cognitiva)

> Contrato de papel do **motor de automações** do JARVIS. Diferente dos outros arquivos de
> `agents/`, este não descreve uma IA que constrói o JARVIS: descreve um **componente de
> runtime** — o orquestrador de workflows. Deriva de `../architecture/API_ECOSYSTEM.md`,
> `../architecture/EVENT_ARCHITECTURE.md` e da Constituição. Estado: `[PARCIAL]` — o
> conceito e a integração por capacidade existem; o parque de "milhares de automações" é a
> evolução.

## Papel

**Motor de execução de automações.** O n8n (auto-hospedado) conecta serviços e executa
fluxos de trabalho — muitos, potencialmente milhares. É onde uma intenção do Kernel vira uma
sequência concreta de passos integrando APIs, dispositivos e serviços.

## A linha inviolável: sem autoridade cognitiva

**O n8n executa; o Kernel decide.** Esta é a regra que o define:

- O n8n **não** raciocina sobre objetivos, não escolhe o que fazer, não altera memória
  cognitiva, não fala pelo JARVIS.
- Um workflow é disparado por um **evento** ou por uma **decisão do Kernel**, roda seus
  passos, e **publica um evento de conclusão** (sucesso/falha). Ponto.
- Toda inteligência permanece no Kernel; o n8n é "as mãos", nunca "a mente".

## Como se encaixa

```
Kernel decide  →  aciona capacidade "Automation"  →  n8n executa o workflow
                                                        ↓
                                             publica evento de conclusão
                                                        ↓
                                        Kernel/Memória reagem ao resultado
```

- Muitas **capacidades** do catálogo (ver `../architecture/API_ECOSYSTEM.md`) podem ser
  realizadas como workflows n8n — sem que isso mude o Kernel.
- O n8n **assina eventos** (ver `../architecture/EVENT_ARCHITECTURE.md`) para disparar
  fluxos e **publica eventos** de resultado.

## Segurança e "só meu"

- **Auto-hospedado**, na infraestrutura privada do dono; nada de nuvem pública de terceiros
  como cérebro.
- **Contido e com menor privilégio** (ver `../engineering/SECURITY_POLICY.md`): um workflow
  comprometido não alcança o cofre, a memória bruta nem dispositivos fora do seu escopo.
- **Segredos** usados por workflows vêm do cofre sob o mesmo regime (Fernet, nunca em claro,
  nunca logados).
- **Auditável:** cada execução deixa trilha (o quê rodou, quando, com que resultado).
- **Confirmação para efeitos irreversíveis** vale também aqui: um workflow que apaga, gasta
  ou envia passa pela política de confirmação.

## Relação com os agentes de runtime

Os **Diretores** e agentes temporários (ver `../architecture/AGENT_SYSTEM.md`) **podem usar**
o n8n como ferramenta de execução, mas a autoridade continua no Kernel/Diretor. O n8n nunca
é promovido a decisor — nem por um agente, nem por um workflow "esperto".

## Não-objetivos

- Não é um segundo cérebro paralelo.
- Não guarda a memória canônica do JARVIS.
- Não decide, não prioriza, não fala pelo dono. Executa o que foi decidido.
