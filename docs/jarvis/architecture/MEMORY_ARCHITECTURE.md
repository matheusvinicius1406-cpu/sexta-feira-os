# Arquitetura de Memória

> A memória é o que dá **continuidade** e **identidade** ao JARVIS. Deriva da Constituição
> (persistência cognitiva; "só meu"). Estado atual: `[PARCIAL]` — o grafo de conhecimento
> com relações nomeadas e embeddings locais já existe; as categorias abaixo formalizam a
> evolução para uma memória multi-camada completa.

## Princípios da memória

1. **Permanente e local.** A memória nunca se apaga por "reinício" e nunca sai do controle
   do dono. Segredos e dados sensíveis criptografados em repouso.
2. **Multi-categoria.** Diferentes tipos de memória com finalidades distintas (abaixo).
3. **Conectada.** Toda informação relevante é ligada por **relações nomeadas** (grafo).
4. **Recuperável.** Busca semântica (vetorial) + expansão pelo grafo (pensamento em rede).
5. **Substituível.** O motor de armazenamento e o índice vetorial são módulos trocáveis.
6. **Com esquecimento controlado.** Importância/decadência e curadoria pelo dono; esquecer
   é uma operação de primeira classe, sempre auditável.

## Categorias de memória

| Categoria | O que guarda | Exemplos |
|---|---|---|
| **Episódica** `[PARCIAL]` | eventos vividos | conversas, sessões, projetos, viagens |
| **Semântica** `[PARCIAL]` | conhecimento aprendido | livros, artigos, cursos, documentação |
| **Procedural** `[FUTURO]` | como executar tarefas | fluxos, scripts, métodos, automações |
| **Social** `[FUTURO]` | pessoas e relações | contatos, preferências, histórico social |
| **Temporal** `[FUTURO]` | linha do tempo da vida | cronologia contínua de fatos e decisões |
| **Vetorial** `[ATUAL]` | busca semântica | embeddings locais para similaridade |
| **Grafo de conhecimento** `[ATUAL]` | tudo conectado | nós + arestas nomeadas (Obsidian-like) |

Estas categorias são **vistas** sobre um substrato comum de nós+relações, não bancos
separados obrigatoriamente. Cada nó pode pertencer a mais de uma categoria.

## Grafo de conhecimento (o coração)

- **Nós** = unidades de memória (fato, evento, pessoa, projeto, conceito, procedimento…).
- **Arestas** = relações **nomeadas** ("trabalha em", "gosta de", "depende de"), com peso e
  origem (semântica, wikilink, manual, inferida por IA).
- **Recuperação em rede:** busca por similaridade encontra sementes; a expansão pelas
  arestas traz o contexto conectado — o efeito "segundo cérebro" (Obsidian + graph DB).

## Fluxo de escrita (aprendizado → memória)

```
Ação/observação → destilar fato durável → criar/atualizar nó →
computar embedding (local) → ligar a nós relacionados (semântico + nomeado) →
registrar origem e importância
```

## Fluxo de leitura (recuperação para contexto)

```
Consulta → embedding → sementes por similaridade →
expansão pelo grafo (n saltos) → ranqueamento (similaridade + importância) →
injeção no contexto do Kernel
```

## Arquitetura futura (evolução planejada)

- **User Model e World Model** persistidos como sub-grafos de primeira classe (ver
  `WORLD_MODEL.md`).
- **Memória procedural** executável: procedimentos versionados que o Tool Dispatcher pode
  invocar.
- **Índice vetorial escalável** (trocável: em-memória → sqlite-vec/FAISS/pgvector) atrás de
  um contrato estável, sem mudar os chamadores.
- **Compressão/sumarização** de memórias antigas em resumos, preservando referências.
- **Decadência e consolidação** inspiradas em memória humana (curto → longo prazo).
- **Memória especializada por Diretor** (cada agente permanente mantém sua própria; ver
  `AGENT_SYSTEM.md`), sempre sob o mesmo substrato e políticas de privacidade.

## Segurança e privacidade da memória

- Criptografia em repouso para segredos; dados pessoais nunca versionados em git.
- Toda leitura/escrita é auditável.
- O dono pode inspecionar, editar e esquecer qualquer memória (curadoria soberana).
