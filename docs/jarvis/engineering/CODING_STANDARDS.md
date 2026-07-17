# Padrões de Código

> Como o código do JARVIS deve ser escrito para permanecer legível, testável e substituível
> por décadas. Deriva de `ARCHITECTURAL_PRINCIPLES.md` (modularidade, substituibilidade,
> contratos antes do código). Estado: `[ATUAL]` — reflete e formaliza o que já vale no
> `backend-core/`.

## Filosofia

O código é lido muito mais vezes do que é escrito, e este projeto tem **um único dono por
décadas**. Otimize para clareza e para a facilidade de trocar peças, não para esperteza.
Todo módulo esconde uma decisão de implementação atrás de um contrato estável.

## Linguagens e onde usar

Escolhas com justificativa (nenhuma tecnologia entra sem motivo — ver
`../constitution/DECISION_PROCESS.md`):

| Camada | Linguagem | Justificativa |
|---|---|---|
| **Kernel / backend / cognição** | **Python** | ecossistema de IA/ML e de servidores maduro; velocidade de evolução; onde já vive o `backend-core/`. |
| **Componentes de alto desempenho / segurança de memória** | **Rust** | latência e segurança de memória para partes críticas (ex.: núcleo de eventos, cripto, indexação) quando o perfil exigir — sempre atrás de um contrato, via ADR. |
| **Corpo Android (celular, o corpo principal)** | **Kotlin** (Java moderno na JVM) | linguagem oficial de Android; interop total com o ecossistema Java. |

Regra: **a linguagem é detalhe de implementação de um módulo.** Um módulo pode ser
reescrito em outra linguagem sem quebrar seus chamadores, desde que honre o contrato. Trocar
a linguagem de um módulo existente exige ADR.

## Princípios de estilo

1. **Contrato antes do código.** Defina a interface (entradas, saídas, erros) antes de
   implementar. O chamador depende do contrato, nunca da implementação.
2. **Injeção de dependência.** Componentes recebem suas dependências (ver `core/di.py`);
   nada instancia serviços globais escondidos. Isso é o que torna tudo substituível e
   testável.
3. **Funções pequenas e nomes honestos.** O nome diz o que a função faz; se precisa de "e"
   no nome, provavelmente faz coisas demais.
4. **Sem estado global mutável.** Estado vive em componentes explícitos (World Model,
   Memória), nunca em variáveis de módulo.
5. **Erros explícitos.** Falhas são tratadas, não engolidas. Degradação graciosa é uma
   decisão consciente, não um `except: pass`.
6. **Determinismo onde importa.** Lógica de negócio (ex.: `run_due` do scheduler) é
   separada de efeitos (tempo, rede, I/O) para ser testável de forma determinística.
7. **Type hints obrigatórios** no Python de domínio; assinaturas são parte do contrato.

## Ferramentas e portões (o que a CI exige)

- **Lint/format:** `ruff` (lint + formatação) sem erros. Import ordering, variáveis não
  ambíguas, `raise ... from`, imports de `collections.abc` quando cabível — o `ruff` é a
  fonte da verdade.
- **Migrações:** `alembic upgrade head` aplica limpo (ver `../architecture/` e o schema em
  `models/`).
- **Testes:** `pytest` verde (ver `TESTING_STRATEGY.md`).

Um PR só é considerado pronto com **os três verdes**. Ver `GIT_WORKFLOW.md`.

## Convenções específicas do domínio

- **Nada de LLM na nuvem.** Nenhum import, chamada ou dependência de provedor externo de
  modelo entra no código (ver `../constitution/JARVIS_CONSTITUTION.md`, princípio "só meu" e
  "LLM substituível"). Inferência é local, atrás do contrato do `LocalBrain`.
- **Segredos nunca em código nem em log.** Chaves ficam no cofre (Fernet); nunca são
  retornadas nem registradas (ver `SECURITY_POLICY.md`).
- **O Kernel não executa ferramentas diretamente.** Toda ação externa passa pelo Tool
  Dispatcher / adaptadores de capacidade (ver `../architecture/API_ECOSYSTEM.md`).
- **Dados pessoais nunca versionados** em git (ver `SECURITY_POLICY.md` e
  `DOCUMENTATION_RULES.md`).

## Comentários e documentação no código

- Comente **por quê**, não **o quê** (o código já diz o quê).
- Comente na densidade e no idioma do arquivo ao redor.
- Decisões arquiteturais **não** vivem em comentários — vivem em ADRs (`../adr/`).
