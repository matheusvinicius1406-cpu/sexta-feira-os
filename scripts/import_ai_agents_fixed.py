#!/usr/bin/env python3
"""
Importa 50 AI Agents corrigidos (nomes unicos nos nos).
"""
import json, uuid, urllib.request, urllib.error, os
from pathlib import Path

API_KEY = os.environ.get("N8N_API_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyMDkwNGFkOC1iYjQ0LTQyOGEtYWVhZi1iZDA3OGIzMmNkOGIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNmQ4MjYzODktNzVmNy00Njg0LWEyNzYtZGUzZTY1MWU2Nzc2IiwiaWF0IjoxNzg0NDY0ODY5fQ.lP1NWKLlwx9_hVXN55rtRd_N79-DQWOEgTUASSih2RU"
BASE_URL = "http://127.0.0.1:5678"
CALLBACK_SECRET = "Si3hkdlTApTEPcIbo2Giqly1KWU9gMtmjruu00yKymo"
KERNEL_URL = "http://host.docker.internal:8000"
OUTPUT_DIR = Path("scripts/n8n-workflows/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 50 AI AGENTS
AI_AGENTS = []

categories = {
    "pesquisa": [
        "Pesquisador Web", "Pesquisador Docs", "Pesquisador Codigo",
        "Pesquisador Cientifico", "Analista Noticias", "Analista Mercado",
        "Analista Redes", "Analista Dados", "Curador Conteudo", "Bibliotecario",
    ],
    "escritor": [
        "Redator", "Copywriter", "Jornalista", "Blogueiro",
        "Email Marketing", "Social Media", "Relatorio", "Resumidor", "Tradutor", "Revisor",
    ],
    "analista": [
        "Analista Dados", "Analista Tendencias", "Analista Sentimentos",
        "Analista Riscos", "Analista Custos", "Analista Performance",
        "Analista Concorrencia", "Analista SWOT", "Analista Impacto", "Analista ROI",
    ],
    "planejador": [
        "Planejador Projetos", "Planejador Tarefas", "Planejador Estudos",
        "Planejador Viagem", "Planejador Financas", "Planejador Carreira",
        "Planejador Dieta", "Planejador Treino", "Planejador Eventos", "Estrategista",
    ],
    "assistente": [
        "Assistente Pessoal", "Assistente Agenda", "Assistente Email",
        "Assistente Compras", "Assistente Receitas", "Assistente Tech",
        "Assistente Saude", "Assistente Estudos", "Conselheiro", "Mentor",
    ],
}

for cat, roles in categories.items():
    for i, role in enumerate(roles):
        AI_AGENTS.append({
            "id": f"agent-{cat}-{i+1:02d}",
            "name": f"AI {cat.title()}: {role}",
            "webhook_path": f"sexta/agent/{cat}/{i+1:02d}",
            "system_prompt": f"Voce e {role}, um sub-agente especialista da Sexta-Feira. Seja conciso e direto. Responda em portugues.",
            "role": role,
            "category": cat,
        })

print(f"Gerando {len(AI_AGENTS)} AI agents...")

def import_workflow(wf_json):
    payload = json.dumps({
        "name": wf_json["name"],
        "nodes": wf_json["nodes"],
        "connections": wf_json["connections"],
        "settings": {},
    })
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/workflows",
        data=payload.encode("utf-8"),
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("id", "?")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        print(f"  ERRO {e.code}: {body}")
        return None

ok = 0
fail = 0

for a in AI_AGENTS:
    print(f"Criando: {a['name']}...", end=" ")

    # Build nodes with UNIQUE names
    webhook = {
        "parameters": {"httpMethod": "POST", "path": a["webhook_path"],
                       "responseMode": "onReceived", "responseData": "allEntries", "options": {}},
        "id": str(uuid.uuid4())[:8], "name": "Webhook",
        "type": "n8n-nodes-base.webhook", "typeVersion": 1.1,
        "position": [250, 300],
    }

    recall = {
        "parameters": {
            "url": f"{KERNEL_URL}/api/v1/automations/callback",
            "authentication": "none", "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "action", "value": "recall"},
                    {"name": "params", "value": '{"query": "={{ $json.body.message }}"}', "parameterType": "string"},
                ]
            },
            "headerParameters": {
                "parameters": [
                    {"name": "X-N8N-Callback-Secret", "value": f"={{ $env.N8N_CALLBACK_SECRET }}"},
                    {"name": "Content-Type", "value": "application/json"},
                ]
            },
            "options": {"timeout": 30000},
        },
        "id": str(uuid.uuid4())[:8], "name": "Buscar Memoria",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [450, 250],
    }

    world = {
        "parameters": {
            "url": f"{KERNEL_URL}/api/v1/automations/callback",
            "authentication": "none", "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "action", "value": "world"},
                    {"name": "params", "value": "{}", "parameterType": "string"},
                ]
            },
            "headerParameters": {
                "parameters": [
                    {"name": "X-N8N-Callback-Secret", "value": f"={{ $env.N8N_CALLBACK_SECRET }}"},
                    {"name": "Content-Type", "value": "application/json"},
                ]
            },
            "options": {"timeout": 15000},
        },
        "id": str(uuid.uuid4())[:8], "name": "Ler Contexto",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [450, 450],
    }

    ollama = {
        "parameters": {
            "url": "http://host.docker.internal:11434/api/chat",
            "authentication": "none", "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "model", "value": "llama3.2"},
                    {"name": "messages", "value": json.dumps([
                        {"role": "system", "content": a["system_prompt"]},
                        {"role": "user", "content": (
                            "Pergunta: {{ $json.body.message }}\n\n"
                            "Memoria recuperada: {{ $('Buscar Memoria').item.json.results }}\n\n"
                            "Contexto atual: {{ $('Ler Contexto').item.json.state }}"
                        )},
                    ])},
                    {"name": "stream", "value": False},
                    {"name": "options", "value": '{"temperature": 0.7, "num_predict": 1024}'},
                ]
            },
            "options": {"timeout": 60000},
        },
        "id": str(uuid.uuid4())[:8], "name": "Raciocinar",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [750, 350],
    }

    remember = {
        "parameters": {
            "url": f"{KERNEL_URL}/api/v1/automations/callback",
            "authentication": "none", "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "action", "value": "remember"},
                    {"name": "params", "value": '={"content": "IA ' + a['role'] + ' respondeu sobre: {{ $json.body.message }}", "kind": "ia_conversa", "source": "automation"}', "parameterType": "string"},
                ]
            },
            "headerParameters": {
                "parameters": [
                    {"name": "X-N8N-Callback-Secret", "value": f"={{ $env.N8N_CALLBACK_SECRET }}"},
                    {"name": "Content-Type", "value": "application/json"},
                ]
            },
            "options": {"timeout": 15000},
        },
        "id": str(uuid.uuid4())[:8], "name": "Salvar",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [750, 550],
    }

    fmt = {
        "parameters": {
            "keepOnlySet": True,
            "values": {
                "string": [
                    {"name": "resposta", "value": "={{ $('Raciocinar').item.json.message.content }}"},
                    {"name": "fontes", "value": "={{ $('Buscar Memoria').item.json.count + ' registros consultados' }}"},
                ]
            },
            "options": {},
        },
        "id": str(uuid.uuid4())[:8], "name": "Formatar",
        "type": "n8n-nodes-base.set", "typeVersion": 3.4,
        "position": [1000, 350],
    }

    # Build workflow JSON
    wf = {
        "name": a["name"],
        "nodes": [webhook, recall, world, ollama, remember, fmt],
        "connections": {
            "Webhook": {"main": [[{"node": "Buscar Memoria", "type": "main", "index": 0}, {"node": "Ler Contexto", "type": "main", "index": 0}]]},
            "Buscar Memoria": {"main": [[{"node": "Raciocinar", "type": "main", "index": 0}]]},
            "Ler Contexto": {"main": [[{"node": "Raciocinar", "type": "main", "index": 0}]]},
            "Raciocinar": {"main": [[{"node": "Salvar", "type": "main", "index": 0}, {"node": "Formatar", "type": "main", "index": 0}]]},
            "Salvar": {"main": []},
            "Formatar": {"main": []},
        },
        "settings": {},
    }

    # Save file
    fname = OUTPUT_DIR / f"{a['id']}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)

    # Import
    wid = import_workflow(wf)
    if wid:
        print(f"OK ID={wid}")
        ok += 1
    else:
        print("FAIL")
        fail += 1

print(f"\nRESUMO: {ok} importados, {fail} falhas")
print(f"Arquivos em: {OUTPUT_DIR}")
