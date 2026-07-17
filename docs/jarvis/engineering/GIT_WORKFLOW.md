# Fluxo de Git

> Como as mudanças entram no JARVIS de forma segura, auditável e reversível. Deriva de
> `ARCHITECTURAL_PRINCIPLES.md` (observabilidade, determinismo) e do
> `../constitution/DECISION_PROCESS.md`. Estado: `[ATUAL]`.

## Princípios

1. **`main` é sempre verde.** Nada entra em `main` sem CI verde.
2. **Toda mudança passa por um branch de trabalho** e um PR; `main` não recebe commit
   direto de desenvolvimento de feature.
3. **Histórico é auditoria.** Mensagens de commit explicam a intenção; o histórico é uma
   trilha legível do porquê de cada mudança.
4. **Reversível.** Toda mudança pode ser revertida sem arqueologia.

## Branches

- `main` — linha estável, sempre verde, protegida.
- Branches de trabalho — nomeadas de forma descritiva. O trabalho atual de auditoria/base
  vive em `claude/sexta-feira-os-audit-a9c56s`.
- **Nunca** faça push para um branch que não seja o designado sem permissão explícita.

## Ciclo de uma mudança

```
Problema/Proposta (ADR se arquitetural — ver DECISION_PROCESS.md)
   ↓
Branch de trabalho
   ↓
Commits pequenos e descritivos
   ↓
CI verde (ruff + alembic upgrade + pytest)
   ↓
PR (só quando o dono pedir) → revisão → aprovação
   ↓
Fast-forward para main (main permanece verde e linear)
```

## Mensagens de commit

- Presente/imperativo, foco na **intenção** ("adiciona cofre Fernet para segredos de
  conector"), não no diff mecânico.
- Uma mudança lógica por commit sempre que possível.
- **Não** inclua identificadores de modelo de IA, segredos, tokens, hostnames internos ou
  dados pessoais na mensagem.

## Regras de push (operacional)

- Push com `git push -u origin <branch>`.
- Em falha de **rede**, retry com backoff exponencial (2s, 4s, 8s, 16s), até 4 tentativas.
- Fetch/pull preferencialmente por branch específico.

## Pull Requests

- **Só crie PR quando o dono pedir explicitamente.**
- Se existir template de PR no repositório, use a estrutura dele; pule seções que peçam
  credenciais/segredos/hostnames — descreva apenas as mudanças de código.
- Seja frugal com comentários automáticos em PR/GitHub: comente só quando for genuinamente
  necessário.

## PR já mergeado

Um PR mergeado está encerrado — não se reaproveita para trabalho novo. Trabalho de
acompanhamento reinicia o branch designado a partir da `main` atual (mesmo nome de branch) e
gera um **novo** PR, sem empilhar sobre histórico já mergeado.

## Relação com o processo de decisão

Mudanças **arquiteturais** exigem ADR aprovado **antes** do merge (ver
`../constitution/DECISION_PROCESS.md`). Mudanças de implementação dentro de uma arquitetura
já decidida seguem direto pelo ciclo acima.
