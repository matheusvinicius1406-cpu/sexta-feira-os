# Ecossistema de APIs

> APIs são **capacidades**, não inteligência. Deriva da Constituição (Artigo V). Estado:
> `[PARCIAL/ATUAL]` — já existe um sistema de conectores de API (capacidades definidas pelo
> dono, chaves criptografadas) e o Tool Dispatcher; o catálogo canônico abaixo é o alvo.

## Princípio

Uma API representa **o que o sistema consegue fazer/consultar**, nunca **o que ele
decide**. A inteligência mora no Kernel; as APIs são portas para o mundo. Cada API é
**modular e substituível** atrás de um contrato estável.

## Catálogo canônico de capacidades

Nomes de capacidade (não de fornecedores). Cada uma é um módulo com contrato próprio:

| Capacidade | Função |
|---|---|
| **Memory API** | ler/escrever na Memória Persistente e no grafo |
| **Context API** | consultar World Model / User Model |
| **Knowledge API** | conhecimento, documentos, pesquisa |
| **Learning API** | registrar aprendizado, ajustar comportamento |
| **Automation API** | criar/disparar/otimizar automações (n8n hoje) |
| **Device API** | despachar ações a dispositivos |
| **Communication API** | mensagens, chamadas, notificações |
| **Calendar API** | agenda e compromissos |
| **Internet / Browser API** | busca e navegação na web |
| **Maps API** | localização e navegação |
| **Home Automation API** | luzes, TV, clima, fechaduras, tomadas |
| **Finance API** | dados financeiros (auxílio, nunca aconselhamento regulado) |
| **Health API** | wearables e sinais (auxílio, nunca diagnóstico) |
| **Voice API** | STT/TTS |
| **Vision API** | imagem e OCR |
| **Robotics API** | atuadores/robôs |
| **Security API** | políticas, credenciais, verificação |
| **Developer API** | build, testes, versionamento, ambiente de dev |

Regra: adicionar milhares de integrações concretas **não** muda o Kernel — cada uma é uma
**capacidade** cadastrada atrás destes contratos (hoje: o registro de conectores).

## Tool Dispatcher — o Kernel nunca executa ferramentas diretamente

```
Objetivo
   ↓
Planejamento
   ↓
Seleção da ferramenta/capacidade
   ↓
Execução (via adaptador da capacidade)
   ↓
Validação (resultado dentro do contrato?)
   ↓
Registro (auditoria) → Learning
```

O Dispatcher isola o Kernel dos detalhes de cada API: o Kernel decide *o que* fazer; o
adaptador sabe *como*.

## Segurança das capacidades

- **Sem URL/ação arbitrária a partir do modelo:** o LLM só invoca capacidades **definidas
  pelo dono** (por nome), o que impede que prompt injection vire SSRF/execução arbitrária.
- **Segredos criptografados:** chaves/tokens ficam em cofre (Fernet), nunca retornados nem
  logados.
- **Menor privilégio:** cada capacidade recebe só o acesso necessário.
- **Timeouts e limites:** toda chamada tem tempo e tamanho de resposta limitados.
- **Confirmação para efeitos irreversíveis.**

## Substituibilidade

Trocar um fornecedor (ex.: um provedor de mapas) troca só o **adaptador** daquela
capacidade; o contrato (Maps API) e os chamadores permanecem. Nenhuma capacidade concreta é
dependência dura do núcleo.

## Relação com automações (n8n)

Muitas capacidades podem ser realizadas como **automações** no n8n (ver
`../agents/N8N_ORCHESTRATOR.md`). O n8n é um *motor de execução*: ótimo para integrar
serviços, mas **sem autoridade cognitiva**. O Kernel decide; o n8n executa o workflow.
