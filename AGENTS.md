# AGENTS.md — Sexta-Feira OS

Contrato leve para todos os agentes que trabalham neste repo. A intenção é
**expandir rápido e sem burocracia**: regras mínimas, todas com propósito de
proteção — nada de portões de processo que travam o trabalho.

## Regras que nunca se quebram (proteção real)

- **Nunca commitar segredos reais.** `.env` é gitignored; só `.env.template`
  é versionado. Se um segredo vazar num commit, o fix tem prioridade máxima.
- **Nunca `git push --force` para `main`.** Força-destrutiva é a única coisa
  que pode apagar trabalho dos outros sem deixar rastro.
- **Não rodar comandos destrutivos fora do repo** (rm -rf fora do projeto,
  deletar `.git`, migrations ou `.env`).
- **Testes e lint verdes antes de mergear.** Python: `pytest` + `ruff check
  app tests`. Rust: `cargo test --all-targets`. Android: `assembleDebug`.

## Como trabalhar

- Branches: use qualquer nome que descreva o trabalho (`fix/...`, `feat/...`).
  Sem cerimônia — crie direto com `git checkout -b`.
- Commits: Conventional Commits (`feat(kernel): ...`, `fix(android): ...`).
  Um commit = uma mudança lógica.
- Merge para `main`: direto, sem portão de review obrigatório. Quem mergea é
  responsável por garantir que a suíte não quebrou (rode os testes da área
  afetada antes).
- Ampliar sem medo: refatorar, reestruturar, mudar arquitetura — o código
  existe para evoluir. A única âncora é a suíte de testes: se ela passa e o
  lint limpa, o trabalho está pronto para merge.

## Áreas e comandos (fonte da verdade)

| Área | Lint | Teste |
|------|------|-------|
| Kernel Python (`backend-core/`) | `ruff check app tests` | `python -m pytest` |
| Rust (`src/`, crate raiz) | `cargo check --all-targets` | `cargo test --all-targets` |
| Android (`mobile-android/`) | — | `./gradlew testDebug` (build: `assembleDebug`) |

`scripts/ai/test-all.sh [python|rust|android|all|auto]` roda as suítes certas;
`auto` escolhe pelo diff vs `main`.
