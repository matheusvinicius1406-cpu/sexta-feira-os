# Teia — guia prático das automações

> Como usar o motor de automação da Sexta-Feira OS no dia a dia. A arquitetura está em
> `AUTOMATION_PLATFORM.md`; a decisão, em `../adr/ADR-0013-python-first-automation-platform.md`.

A Teia roda **dentro do kernel**. Não há serviço para subir, painel para abrir nem porta
para expor: se o kernel está de pé, as automações estão. Tudo em Python, tudo nesta máquina.

## Como uma automação funciona

Uma automação é um **grafo dirigido** de nós. O **orquestrador** decide quais nós já podem
rodar; os **operários** (um pool de workers) executam um nó cada. Nós sem dependência entre
si rodam ao mesmo tempo.

Cada aresta de um nó é resolvida exatamente uma vez — ou entregou itens, ou é uma aresta
morta. Quando a última aresta de um nó resolve:

- **alguma entregou** → o nó roda com aqueles itens;
- **todas morreram** → o nó é **pulado**, e o "pulo" desce pelo ramo inteiro.

É essa regra que faz o `se` funcionar: a porta que não disparou não emite nada, então o ramo
não tomado é pulado em vez de rodar vazio.

## Uma automação por inteiro

```yaml
name: Aviso de disco cheio
nodes:
  - id: disco
    type: disco
    config: { caminho: ".", alerta_livre_gb: 10 }
  - id: baixo
    type: se
    config: { esquerda: "{{ nodes.disco.alerta }}", operador: verdadeiro }
  - id: avisar
    type: notificar
    config:
      texto: "Disco baixo: {{ nodes.disco.livre_gb }} GB livres."
connections:
  - { source: disco, target: baixo }
  - { source: baixo, target: avisar, source_port: "true" }
triggers:
  - { id: t1, type: agenda, target: disco, config: { cron: "0 */6 * * *" } }
```

```bash
python -m app.automation.teia.cli validar aviso-disco.yaml
python -m app.automation.teia.cli importar aviso-disco.yaml --slug aviso-disco
python -m app.automation.teia.cli rodar aviso-disco
```

## Expressões `{{ }}`

Um valor de config pode ler o que já aconteceu na execução. É **busca de caminho**, nunca
código: não há `eval`, não há acesso a objetos Python, e por isso uma automação (ou um prompt
que a escreveu) não consegue executar nada através de uma expressão.

| Raiz | O que traz |
|---|---|
| `trigger.*` | os dados que iniciaram a execução |
| `vars.*` | variáveis do workflow (`definir_variaveis` escreve) |
| `nodes.<id>.*` | o **primeiro item** que aquele nó emitiu |
| `all.<id>` | **todos** os itens daquele nó (uma lista) |
| `input` | os itens que chegaram na entrada deste nó |
| `now.*` | `iso`, `date`, `time`, `hour`, `weekday`, `timestamp`… |
| `run.*` | `execution_id`, `workflow`, `trigger`, `owner_id` |
| `secret.NOME` | um segredo do cofre, resolvido na hora da chamada |

Um caminho que não existe é **erro**, não string vazia — uma automação que age sobre `""`
em silêncio é pior que uma que para e diz por quê. Quando o valor é mesmo opcional, use o
padrão:

```yaml
texto: "Olá {{ vars.nome || \"Chefe\" }} — {{ all.metas || [] }}"
```

Uma string que é *só* uma expressão preserva o tipo (`{{ vars.n }}` vira `int`); dentro de
uma frase maior, vira texto.

## Política de execução (por nó)

```yaml
- id: chamada
  type: http
  config: { url: "https://exemplo/api" }
  policy:
    max_attempts: 3          # tentativas (1 = sem retry)
    backoff_seconds: 2       # espera exponencial: 2s, 4s, 8s…
    timeout_seconds: 30      # tempo máximo de UMA tentativa
    on_error: continue       # "fail" derruba a execução; "continue" mata só o ramo
```

Quando um nó falha, a ordem de precedência é:

1. a porta `error` dele está conectada → a falha vira **dado** e segue pelo grafo;
2. `on_error: continue` → o ramo morre, o resto da automação termina;
3. senão → a execução é abortada e registrada como falha, apontando o nó culpado.

## Gatilhos

| Tipo | Config | Quando dispara |
|---|---|---|
| `manual` | — | quando você (ou o Jarvis) pede |
| `agenda` | `{ cron: "0 7 * * 1-5" }` | pela expressão cron, com precisão de minuto |
| `intervalo` | `{ segundos: 300 }` | a cada N segundos (mínimo 30) |
| `evento` | `{ tipo: "objetivo.*" }` | quando um evento do kernel casa com o padrão |
| `webhook` | `{ caminho: "captura", segredo: "" }` | `POST /api/v1/automations/webhook/captura` |

O cron aceita `*`, `n`, `a-b`, `*/passo`, listas, nomes (`jan`, `seg`) e atalhos (`@diario`,
`@semanal`). Fuso em `TEIA_TIMEZONE`; vazio usa o horário da máquina.

Um gatilho de agenda dispara **uma vez por minuto casado** mesmo que o kernel reinicie no
meio do minuto — quem garante isso é a trilha de execuções, não a memória do processo.

Automações reativas não se auto-disparam (um evento cuja origem é a própria automação é
ignorado) e têm teto de disparos por minuto (`TEIA_EVENT_FIRES_PER_MINUTE`), para que duas
automações não fiquem se cutucando para sempre.

## Os nós disponíveis

### fluxo
| tipo | o que faz | saídas |
|---|---|---|
| `inicio` | Ponto de entrada. Emite os dados do gatilho como um item. | main |
| `se` | Desvia o fluxo conforme uma condição. | true, false |
| `escolher` | Roteia para a primeira porta cujo caso casar (senão 'default'). | default, a, b, c, d, e |
| `juntar` | Reúne itens de várias entradas em uma saída. | main |
| `definir_variaveis` | Grava valores em `vars.*` para os nós seguintes. | main |
| `esperar` | Aguarda alguns segundos antes de continuar. | main |
| `parar` | Encerra o ramo. Com `erro: true`, derruba a execução. | — |
| `nada` | Passa os itens adiante sem alterar nada. | main |
| `sub_automacao` | Executa outra automação e devolve o resultado. | main, error |

### dados
| tipo | o que faz | saídas |
|---|---|---|
| `texto` | Monta um texto a partir de expressões. | main |
| `json_ler` | Converte texto JSON (inclusive cercado por ```) em item. | main |
| `filtrar` | Mantém só os itens que passam na condição. | main |
| `mapear` | Reescreve cada item escolhendo e renomeando campos. | main |
| `ordenar` | Ordena os itens por um campo. | main |
| `limitar` | Mantém apenas os primeiros N itens. | main |
| `agregar` | Reduz a lista a um item (contar/somar/media/minimo/maximo/juntar). | main |

### kernel — o segundo cérebro
| tipo | o que faz | saídas |
|---|---|---|
| `memoria_gravar` | Guarda um fato duradouro no segundo cérebro. | main, error |
| `memoria_buscar` | Procura na memória e emite os resultados. | main, error |
| `mundo_definir` | Atualiza um fato do presente (World Model). | main, error |
| `mundo_ler` | Lê um fato do presente, ou o retrato inteiro. | main, error |
| `dono_anotar` | Grava um traço duradouro do dono (User Model). | main, error |
| `evento_publicar` | Emite um evento no barramento do kernel. | main, error |
| `agendar` | Cria um lembrete ou uma ação futura. | main, error |
| `notificar` | Envia um aviso para um dispositivo do dono. | main, error |
| `dispositivo_acao` | Manda um corpo do dono executar uma ação nativa. | main, error |
| `capacidade` | Executa uma capacidade de API cadastrada pelo dono. | main, error |
| `meta_criar` / `meta_listar` | Cria e lista objetivos. | main, error |
| `decidir` | Escolhe o próximo foco, com a justificativa. | main, error |
| `briefing` | Produz o relatório do segundo cérebro. | main, error |
| `diario_escrever` | Adiciona uma entrada datada ao diário. | main, error |
| `aprender` | Grava a lição de um resultado observado. | main, error |

### ia (cérebro local)
| tipo | o que faz | saídas |
|---|---|---|
| `ia_perguntar` | Envia um prompt ao Ollama local e emite a resposta. | main, error |
| `ia_json` | Pede um JSON ao cérebro local e devolve o objeto lido. | main, error |
| `ia_resumir` | Resume um texto usando o cérebro local. | main, error |

### rede, arquivos e sistema
| tipo | o que faz | saídas |
|---|---|---|
| `http` | Chama uma URL (GET/POST/…) e emite a resposta. | main, error |
| `arquivo_ler` | Lê um arquivo (texto, linhas ou CSV). | main, error |
| `arquivo_escrever` | Grava ou acrescenta em um arquivo. | main, error |
| `arquivo_existe` | Verifica um caminho sem falhar quando não existe. | main, error |
| `pasta_listar` | Emite os arquivos de uma pasta. | main, error |
| `disco` | Mede o espaço livre e marca alerta. | main, error |
| `backup_banco` | Backup consistente do banco + rotação. | main, error |
| `cerebro_saude` | Verifica se o Ollama local responde. | main, error |
| `programa` | Roda um programa da lista permitida (desligado por padrão). | main, error |

## As automações que já vêm prontas

Instaladas no primeiro boot (`TEIA_SEED_CATALOG=true`). Só usam capacidades locais — nenhuma
precisa de conta ou chave de API. As que falariam com você sem ser chamadas vêm
**desligadas**; ligue com `POST /api/v1/automations/{slug}/enable`.

| Slug | Quando | O que faz | Padrão |
|---|---|---|---|
| `briefing-matinal` | 07:00 | gera o briefing do dia e te avisa | desligada |
| `foco-do-dia` | 08:30, dias úteis | decide seu foco e avisa (silencia se não houver meta) | desligada |
| `guardiao-das-metas` | 09:00 | avisa quantas metas estão abertas | desligada |
| `sentinela-do-cerebro` | a cada 5 min | checa o Ollama e registra no World Model | **ligada** |
| `vigia-do-disco` | a cada 6 h | avisa se sobrar menos de 10 GB | **ligada** |
| `backup-do-kernel` | 03:00 | backup do banco, mantém 7 cópias | **ligada** |
| `captura-rapida` | webhook | guarda a ideia na memória e no inbox do dia | **ligada** |
| `celebrar-meta` | evento | ao concluir uma meta, registra e avisa | **ligada** |
| `revisao-noturna` | 22:00 | o cérebro local revisa seu dia e escreve no diário | desligada |
| `revisao-semanal` | domingo 18:00 | destila a semana em uma memória duradoura | desligada |

Captura rápida, na prática:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/automations/webhook/captura \
     -H 'Content-Type: application/json' \
     -d '{"texto":"ideia: usar a Teia pra fechar o expediente"}'
```

## API

| Rota | O que faz |
|---|---|
| `GET /api/v1/automations/status` | saúde do motor |
| `GET /api/v1/automations/types` | JSON Schema de todo node e gatilho |
| `GET /api/v1/automations` | lista (`?busca=`) |
| `POST /api/v1/automations` | cria/atualiza (`definicao` JSON ou `yaml`) |
| `POST /api/v1/automations/validate` | valida sem salvar |
| `POST /api/v1/automations/{slug}/run` | executa agora |
| `POST /api/v1/automations/{slug}/enable` | liga/desliga |
| `DELETE /api/v1/automations/{slug}` | remove |
| `GET /api/v1/automations/executions` | trilha de execuções (`?automacao=`) |
| `GET /api/v1/automations/executions/{id}` | uma execução, nó a nó |
| `POST /api/v1/automations/executions/{id}/cancel` | cancela uma execução em andamento |
| `POST /api/v1/automations/catalog/install` | instala as prontas (não sobrescreve as suas) |
| `POST /api/v1/automations/webhook/{caminho}` | dispara por webhook |

## CLI

```bash
python -m app.automation.teia.cli listar
python -m app.automation.teia.cli nos                 # todos os tipos de nó
python -m app.automation.teia.cli rodar backup-do-kernel
python -m app.automation.teia.cli historico backup-do-kernel
python -m app.automation.teia.cli exportar briefing-matinal --saida b.yaml
python -m app.automation.teia.cli catalogo
```

O CLI roda **fora** do processo do FastAPI, contra o mesmo banco: funciona com o kernel de
pé ou não. Ações destinadas a um dispositivo ficam na fila do banco e são entregues quando
ele conectar — exatamente como o kernel faria.

## O que o Jarvis pode fazer sozinho

Pela conversa, o cérebro tem `run_automation`, `list_automations` e `automation_history`.
Ele **executa** o que existe; **criar e editar** continua sendo seu, pela API ou pelo CLI.
Assim, o alcance máximo de um prompt envenenado é o conjunto de automações que você já
aprovou.

## Limites e cercas

| Cerca | Onde se ajusta | Para quê |
|---|---|---|
| nós simultâneos | `TEIA_MAX_PARALLEL` | não abrir 50 conexões de uma vez |
| nós por execução | `TEIA_MAX_NODES_PER_RUN` | laço infinito |
| tempo de execução | `TEIA_RUN_TIMEOUT_SECONDS` | execução travada |
| profundidade | `TEIA_MAX_DEPTH` | recursão de `sub_automacao` |
| disparos por evento | `TEIA_EVENT_FIRES_PER_MINUTE` | automações se cutucando |
| pastas de arquivo | `TEIA_WORKSPACE`, `TEIA_ALLOWED_PATHS` | `../../` não sai da cerca |
| programas locais | `TEIA_SHELL_ENABLED`, `TEIA_SHELL_ALLOWLIST` | desligado por padrão; sem shell |

Segredos ficam no cofre Fernet e entram só por `{{ secret.NOME }}`, no momento da chamada.
O valor resolvido é raspado de tudo que a Teia grava ou registra — a trilha de auditoria
guarda `***`, nunca o segredo.
