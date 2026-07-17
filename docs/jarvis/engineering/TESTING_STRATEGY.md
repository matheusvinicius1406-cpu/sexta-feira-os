# Estratégia de Testes

> Como garantimos que o JARVIS funciona e continua funcionando enquanto evolui por décadas.
> Deriva de `ARCHITECTURAL_PRINCIPLES.md` (determinismo, degradação graciosa,
> substituibilidade). Estado: `[ATUAL]` — a suíte `pytest` do `backend-core/` já é o portão.

## Por que testamos

Um "segundo cérebro" que perde memória ou executa a ação errada é pior que inútil. Testes
são o que permite **trocar peças com confiança** (substituibilidade) sem regressão. Todo
contrato tem um teste que o prova.

## O que testar (pirâmide)

1. **Testes de contrato/unidade (base, a maioria).** Cada componente atrás de um contrato é
   testado isoladamente com dependências injetadas (fakes/stubs). Ex.: memória, scheduler,
   cofre, dispatcher, bus.
2. **Testes de integração (meio).** Fluxos entre componentes reais: pareamento de
   dispositivo → comando → entrega; conector → chamada de capacidade; loop de tool-calling.
3. **Testes de ponta a ponta (topo, poucos).** Cenários do dono ponta a ponta, sobre modelo
   local, quando fizer sentido.

## Princípios de teste

- **Determinismo acima de tudo.** Lógica é separada de efeitos (tempo, rede, aleatoriedade)
  para ser testada de forma determinística. Ex.: o scheduler expõe um `run_due` puro,
  testado sem esperar o relógio; o loop de fundo apenas o chama.
- **Sem dependência de rede externa nem de nuvem** nos testes. Coerente com "só meu":
  nenhum teste chama LLM externo. Inferência local é isolada atrás de um fake do
  `LocalBrain`.
- **Degradação graciosa é testada explicitamente.** Quando uma capacidade opcional está
  ausente (ex.: voz/STT/TTS indisponível), o teste força a indisponibilidade (monkeypatch)
  e verifica que o sistema degrada em vez de quebrar — independente do que está instalado na
  máquina de CI.
- **Migrações fazem parte do teste.** `alembic upgrade head` roda na CI; o schema é
  verificado, não presumido.
- **Idempotência e ordenação** de eventos/assinantes têm testes próprios (ver
  `../architecture/EVENT_ARCHITECTURE.md`).

## Portão de CI (obrigatório para todo PR)

```
ruff check            # lint/format sem erros
alembic upgrade head  # migrações aplicam limpo
pytest                # suíte verde
```

Os três verdes = pronto para revisão. Nenhum merge com CI vermelha (ver `GIT_WORKFLOW.md`).

## Cobertura — o que importa

Não perseguimos um número de cobertura; perseguimos **contratos provados** e **caminhos de
falha exercitados**. Prioridade de cobertura:
1. Segurança e privacidade (cofre, escopo do dono, não-vazamento de segredo).
2. Memória (não perder/ corromper; recuperação correta).
3. Ações no mundo real (despacho correto, confirmação de efeitos irreversíveis).
4. Determinismo do scheduler e do event bus.

## Ao adicionar um componente novo

Todo componente novo entra com: (a) seu contrato, (b) testes de unidade do contrato, (c)
teste do caminho de falha/degradação. Sem isso, não passa no portão.
