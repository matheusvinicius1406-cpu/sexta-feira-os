# 🤖 Workflows n8n — Sexta-Feira OS

Workflows prontos para importar no n8n que conectam ao Kernel Sexta-Feira.

## Como importar

1. Abra o n8n no navegador: `http://localhost:5678`
2. Clique em **Workflows → Add Workflow → Import from File**
3. Selecione o arquivo `.json` desejado

## Configuração necessária no n8n

Antes de usar, configure a variável de ambiente no n8n:

**Settings → Environment Variables → Add Variable**

| Nome | Valor |
|------|-------|
| `N8N_CALLBACK_SECRET` | `Si3hkdlTApTEPcIbo2Giqly1KWU9gMtmjruu00yKymo` |

*Este é o mesmo segredo configurado no `.env` do kernel.*

## Workflows disponíveis

| Arquivo | Função |
|---------|--------|
| `sexta-feira-kernel-bridge.json` | Ponte genérica — chama qualquer ação do kernel |
| `sexta-feira-ai-agent.json` | Sub-agente de IA (usa Ollama dentro do n8n) |

## URL do Kernel

- Se o n8n roda em **Docker Desktop**: `http://host.docker.internal:8000`
- Se o n8n roda **fora do Docker**: `http://127.0.0.1:8000`

Ajuste a URL no nó **HTTP Request** de cada workflow se necessário.
