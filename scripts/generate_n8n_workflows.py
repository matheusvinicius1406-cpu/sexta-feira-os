#!/usr/bin/env python3
"""
Gerador de Workflows n8n para Sexta-Feira OS.
Cria 100 automacoes + 50 AI agentes/sub-agentes e importa via API.
"""
import json
import uuid
import urllib.request
import urllib.error
import sys
from pathlib import Path

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyMDkwNGFkOC1iYjQ0LTQyOGEtYWVhZi1iZDA3OGIzMmNkOGIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNmQ4MjYzODktNzVmNy00Njg0LWEyNzYtZGUzZTY1MWU2Nzc2IiwiaWF0IjoxNzg0NDY0ODY5fQ.lP1NWKLlwx9_hVXN55rtRd_N79-DQWOEgTUASSih2RU"
BASE_URL = "http://127.0.0.1:5678"
CALLBACK_SECRET = "Si3hkdlTApTEPcIbo2Giqly1KWU9gMtmjruu00yKymo"
KERNEL_URL = "http://host.docker.internal:8000"

OUTPUT_DIR = Path("scripts/n8n-workflows/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_webhook(path):
    return {
        "parameters": {"httpMethod": "POST", "path": path, "responseMode": "onReceived", "responseData": "allEntries", "options": {}},
        "id": str(uuid.uuid4())[:8], "name": "Webhook",
        "type": "n8n-nodes-base.webhook", "typeVersion": 1.1,
        "position": [250, 300],
    }


def make_callback(action, query_template="={{ $json.body.message }}", extra_params=""):
    params = {"action": action, "params": {"query": query_template}}
    if extra_params:
        params["params"].update(extra_params)
    return {
        "parameters": {
            "url": f"{KERNEL_URL}/api/v1/automations/callback",
            "authentication": "none", "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": k, "value": json.dumps(v) if isinstance(v, dict) else v}
                    for k, v in params.items()
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
        "id": str(uuid.uuid4())[:8], "name": "Kernel",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [450, 300],
    }


def make_ollama_node(model="llama3.2", system_prompt="Voce e um assistente util.", user_template=""):
    return {
        "parameters": {
            "url": "http://host.docker.internal:11434/api/chat",
            "authentication": "none", "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "model", "value": model},
                    {"name": "messages", "value": json.dumps([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_template or "={{ $json.body.message }}"},
                    ])},
                    {"name": "stream", "value": False},
                    {"name": "options", "value": '{"temperature": 0.7, "num_predict": 1024}'},
                ]
            },
            "options": {"timeout": 60000},
        },
        "id": str(uuid.uuid4())[:8], "name": "Ollama",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [650, 300],
    }


def make_format_response():
    return {
        "parameters": {
            "keepOnlySet": True,
            "values": {"string": [{"name": "result", "value": "={{ $json }}"}]},
            "options": {},
        },
        "id": str(uuid.uuid4())[:8], "name": "Formatar",
        "type": "n8n-nodes-base.set", "typeVersion": 3.4,
        "position": [850, 300],
    }


# ─── 100 AUTOMACOES ─────────────────────────────────────

AUTOMATIONS = []

# 10 - Notificacoes
for i, (name, msg, ch) in enumerate([
    ("WhatsApp", "Mensagem para WhatsApp", "whatsapp"),
    ("Telegram", "Mensagem para Telegram", "telegram"),
    ("Email", "Enviar email", "email"),
    ("SMS", "Enviar SMS", "sms"),
    ("Push Notification", "Notificacao push", "push"),
    ("Slack", "Mensagem no Slack", "slack"),
    ("Discord", "Mensagem no Discord", "discord"),
    ("Teams", "Mensagem no Teams", "teams"),
    ("Signal", "Mensagem no Signal", "signal"),
    ("Matrix", "Mensagem no Matrix", "matrix"),
]):
    AUTOMATIONS.append({
        "id": f"notificacao-{i+1:02d}",
        "name": f"Notificacao: {name}",
        "webhook_path": f"sexta/notificacao/{ch}",
        "action": "event",
        "params": {"type": f"notificacao.{ch}", "payload": {"canal": ch, "mensagem": msg, "destino": "={{ $json.body.destino }}"}},
    })

# 10 - Calendario
for i, (name, action, desc) in enumerate([
    ("Criar Evento", "event", "Criar evento no calendario"),
    ("Ver Agenda", "world", "Ver agenda do dia"),
    ("Lembrete", "schedule", "Criar lembrete"),
    ("Reuniao", "schedule", "Agendar reuniao"),
    ("Compromisso", "schedule", "Criar compromisso"),
    ("Aniversario", "remember", "Lembrar aniversario"),
    ("Feriado", "recall", "Consultar feriados"),
    ("Tarefa", "schedule", "Criar tarefa com prazo"),
    ("Check-in", "schedule", "Agendar check-in"),
    ("Deadline", "schedule", "Definir deadline"),
]):
    AUTOMATIONS.append({
        "id": f"calendario-{i+1:02d}",
        "name": f"Calendario: {name}",
        "webhook_path": f"sexta/calendario/{action}",
        "action": action,
        "params": {"descricao": desc},
    })

# 10 - Clima/Tempo
for i, (name, action) in enumerate([
    ("Clima Agora", "call_api"), ("Previsao 7 Dias", "call_api"),
    ("Alerta Clima", "call_api"), ("Qualidade Ar", "call_api"),
    ("Nascer do Sol", "call_api"), ("Fases da Lua", "call_api"),
    ("Umidade", "call_api"), ("Ventos", "call_api"),
    ("Visibilidade", "call_api"), ("Indice UV", "call_api"),
]):
    AUTOMATIONS.append({
        "id": f"clima-{i+1:02d}",
        "name": f"Clima: {name}",
        "webhook_path": f"sexta/clima/{action.replace('call_api','temp')}",
        "action": "call_api",
        "params": {"capability": "weather_now", "params": {"lat": "={{ $json.body.lat || '-23.55' }}", "lon": "={{ $json.body.lon || '-46.63' }}"}},
    })

# 10 - Casa Inteligente
for i, (device, action) in enumerate([
    ("Luz Sala", "world_set"), ("Luz Quarto", "world_set"), ("Luz Cozinha", "world_set"),
    ("Ar Condicionado", "world_set"), ("Termostato", "world_set"),
    ("Tv", "world_set"), ("Som", "world_set"),
    ("Camera", "world_set"), ("Fechadura", "world_set"),
    ("Cortinas", "world_set"),
]):
    AUTOMATIONS.append({
        "id": f"casa-{i+1:02d}",
        "name": f"Casa: {device}",
        "webhook_path": f"sexta/casa/{action}",
        "action": "action",
        "params": {"device": "celular", "action": action, "params": {"dispositivo": device, "estado": "={{ $json.body.estado || 'ligar' }}"}},
    })

# 10 - Produtividade
for i, (tool, action) in enumerate([
    ("Tarefas", "remember"), ("Checklist", "remember"),
    ("Notas", "remember"), ("Ideias", "remember"),
    ("Projetos", "create_goal"), ("Metas", "create_goal"),
    ("Habitos", "learning"), ("Foco", "world_set"),
    ("Pomodoro", "schedule"), ("Resumo", "recall"),
]):
    AUTOMATIONS.append({
        "id": f"produtividade-{i+1:02d}",
        "name": f"Produtividade: {tool}",
        "webhook_path": f"sexta/produtividade/{action}",
        "action": action,
    })

# 10 - Financas
for i, (name, action) in enumerate([
    ("Cotacao USD", "call_api"), ("Cotacao EUR", "call_api"),
    ("Converter Moeda", "call_api"), ("Gastos", "remember"),
    ("Orcamento", "remember"), ("Investimentos", "recall"),
    ("Fatura Cartao", "remember"), ("Contas Pagar", "schedule"),
    ("Saldo", "recall"), ("Meta Financeira", "create_goal"),
]):
    AUTOMATIONS.append({
        "id": f"financas-{i+1:02d}",
        "name": f"Financas: {name}",
        "webhook_path": f"sexta/financas/{action}",
        "action": action,
    })

# 10 - Desenvolvimento
for i, (name, action) in enumerate([
    ("Git Push", "event"), ("Git Pull", "event"),
    ("Build", "event"), ("Deploy", "event"),
    ("Testes", "event"), ("Code Review", "recall"),
    ("Issue", "remember"), ("PR", "remember"),
    ("Logs", "recall"), ("Metricas", "event"),
]):
    AUTOMATIONS.append({
        "id": f"dev-{i+1:02d}",
        "name": f"Dev: {name}",
        "webhook_path": f"sexta/dev/{action}",
        "action": action,
    })

# 10 - Midia
for i, (name, action) in enumerate([
    ("YouTube", "world_set"), ("Spotify", "world_set"),
    ("Podcast", "world_set"), ("Playlist", "world_set"),
    ("Filme", "remember"), ("Serie", "remember"),
    ("Musica", "world_set"), ("Livro", "remember"),
    ("Artigo", "remember"), ("Noticia", "recall"),
]):
    AUTOMATIONS.append({
        "id": f"midia-{i+1:02d}",
        "name": f"Midia: {name}",
        "webhook_path": f"sexta/midia/{action}",
        "action": action,
    })

# 10 - Saude
for i, (name, action) in enumerate([
    ("Passos", "world_set"), ("Sono", "world_set"),
    ("Agua", "world_set"), ("Refeicao", "remember"),
    ("Exercicio", "remember"), ("Meditacao", "learning"),
    ("Peso", "remember"), ("Batimentos", "world_set"),
    ("Medicamento", "schedule"), ("Checkup", "schedule"),
]):
    AUTOMATIONS.append({
        "id": f"saude-{i+1:02d}",
        "name": f"Saude: {name}",
        "webhook_path": f"sexta/saude/{action}",
        "action": action,
    })

# 10 - Obsidian/Notas
for i, (name, action) in enumerate([
    ("Nova Nota", "remember"), ("Buscar Nota", "recall"),
    ("Diario", "remember"), ("Ideia", "remember"),
    ("Resumo", "recall"), ("Tag", "recall"),
    ("Backup", "event"), ("Listar Notas", "recall"),
    ("Wikititle", "recall"), ("Conceito", "recall"),
]):
    AUTOMATIONS.append({
        "id": f"obsidian-{i+1:02d}",
        "name": f"Obsidian: {name}",
        "webhook_path": f"sexta/obsidian/{action}",
        "action": action,
    })

# 10 - Sistema
for i, (name, action) in enumerate([
    ("Status", "health"), ("Modelos IA", "health"),
    ("Memoria", "recall"), ("Objetivos", "goals"),
    ("Aprendizados", "lessons"), ("Capacidades", "capabilities"),
    ("Dispositivos", "world"), ("Agenda", "world"),
    ("Contexto", "world"), ("Log", "event"),
]):
    AUTOMATIONS.append({
        "id": f"sistema-{i+1:02d}",
        "name": f"Sistema: {name}",
        "webhook_path": f"sexta/sistema/{action}",
        "action": action,
    })

# total automations
print(f"Total automacoes definidas: {len(AUTOMATIONS)}")

# ─── 50 AI AGENTS / SUB-AGENTS ──────────────────────────

AI_AGENTS = []

# 10 - Pesquisadores
for i, (role, task) in enumerate([
    ("Pesquisador Web", "Pesquise na internet sobre: "),
    ("Pesquisador Docs", "Analise a documentacao sobre: "),
    ("Pesquisador Codigo", "Analise o codigo fonte sobre: "),
    ("Pesquisador Cientifico", "Resuma o artigo cientifico sobre: "),
    ("Analista Noticias", "Resuma as principais noticias sobre: "),
    ("Analista Mercado", "Analise o mercado de: "),
    ("Analista Redes", "Pesquise nas redes sociais sobre: "),
    ("Analista Dados", "Analise os dados sobre: "),
    ("Curador Conteudo", "Selecione os melhores conteudos sobre: "),
    ("Bibliotecario", "Encontre referencias sobre: "),
]):
    AI_AGENTS.append({
        "id": f"agent-pesquisa-{i+1:02d}",
        "name": f"AI Pesquisador: {role}",
        "webhook_path": f"sexta/agent/pesquisa/{i+1:02d}",
        "system_prompt": (
            f"Voce e {role}, um sub-agente especialista da Sexta-Feira. "
            "Pesquise na memoria primeiro, depois raciocine com base no que encontrar. "
            "Seja conciso e direto, entregue resultados acionaveis."
        ),
    })

# 10 - Escritores
for i, (role, task) in enumerate([
    ("Redator", "Escreva um texto sobre: "),
    ("Copywriter", "Crie uma copia de marketing para: "),
    ("Jornalista", "Escreva uma noticia sobre: "),
    ("Blogueiro", "Crie um post de blog sobre: "),
    ("Email Marketing", "Escreva um email sobre: "),
    ("Social Media", "Crie uma postagem para redes sociais sobre: "),
    ("Relatorio", "Escreva um relatorio sobre: "),
    ("Resumidor", "Resuma o seguinte conteudo: "),
    ("Tradutor", "Traduza o seguinte para portugues: "),
    ("Revisor", "Revise e corrija o seguinte texto: "),
]):
    AI_AGENTS.append({
        "id": f"agent-escritor-{i+1:02d}",
        "name": f"AI Escritor: {role}",
        "webhook_path": f"sexta/agent/escritor/{i+1:02d}",
        "system_prompt": (
            f"Voce e {role}, um sub-agente especialista da Sexta-Feira. "
            "Escreva em portugues claro e profissional. "
            "Adapte o tom conforme o contexto fornecido."
        ),
    })

# 10 - Analistas
for i, (role, task) in enumerate([
    ("Analista Dados", "Analise os seguintes dados: "),
    ("Analista Tendencias", "Identifique tendencias em: "),
    ("Analista Sentimentos", "Analise o sentimento de: "),
    ("Analista Riscos", "Avalie os riscos de: "),
    ("Analista Custos", "Analise os custos de: "),
    ("Analista Performance", "Avalie a performance de: "),
    ("Analista Concorrencia", "Analise a concorrencia de: "),
    ("Analista SWOT", "Faca analise SWOT de: "),
    ("Analista Impacto", "Avalie o impacto de: "),
    ("Analista ROI", "Calcule o ROI de: "),
]):
    AI_AGENTS.append({
        "id": f"agent-analista-{i+1:02d}",
        "name": f"AI Analista: {role}",
        "webhook_path": f"sexta/agent/analista/{i+1:02d}",
        "system_prompt": (
            f"Voce e {role}, um sub-agente analista da Sexta-Feira. "
            "Use dados e logicas para suas analises. "
            "Seja objetivo e apresente conclusoes claras."
        ),
    })

# 10 - Planejadores
for i, (role, task) in enumerate([
    ("Planejador Projetos", "Planeje o projeto: "),
    ("Planejador Tarefas", "Organize as tarefas: "),
    ("Planejador Estudos", "Crie um plano de estudos para: "),
    ("Planejador Viagem", "Planeje uma viagem para: "),
    ("Planejador Financas", "Planeje as financas para: "),
    ("Planejador Carreira", "Planeje a carreira em: "),
    ("Planejador Dieta", "Crie um plano alimentar para: "),
    ("Planejador Treino", "Crie um plano de treinos para: "),
    ("Planejador Eventos", "Planeje o evento: "),
    ("Estrategista", "Crie uma estrategia para: "),
]):
    AI_AGENTS.append({
        "id": f"agent-planejador-{i+1:02d}",
        "name": f"AI Planejador: {role}",
        "webhook_path": f"sexta/agent/planejador/{i+1:02d}",
        "system_prompt": (
            f"Voce e {role}, um sub-agente planejador da Sexta-Feira. "
            "Crie planos detalhados e acionaveis com prazos. "
            "Considere recursos, tempo e prioridades."
        ),
    })

# 10 - Assistentes
for i, (role, task) in enumerate([
    ("Assistente Pessoal", "Ajude com: "),
    ("Assistente Agenda", "Gerencie a agenda: "),
    ("Assistente Email", "Gerencie os emails: "),
    ("Assistente Compras", "Ajude com compras: "),
    ("Assistente Receitas", "Sugira receitas para: "),
    ("Assistente Tech", "Ajude com tecnologia: "),
    ("Assistente Saude", "Ajude com saude: "),
    ("Assistente Estudos", "Ajude com estudos: "),
    ("Conselheiro", "De conselhos sobre: "),
    ("Mentor", "Seja mentor em: "),
]):
    AI_AGENTS.append({
        "id": f"agent-assistente-{i+1:02d}",
        "name": f"AI Assistente: {role}",
        "webhook_path": f"sexta/agent/assistente/{i+1:02d}",
        "system_prompt": (
            f"Voce e {role}, um assistente pessoal da Sexta-Feira. "
            "Seja prestativo, amigavel e eficiente. "
            "Use o contexto da memoria para personalizar suas respostas."
        ),
    })

print(f"Total AI agentes definidos: {len(AI_AGENTS)}")


# ─── GERAR WORKFLOWS ────────────────────────────────────

def build_workflow_json(name, webhook_path, nodes_list):
    """Build a complete n8n workflow JSON."""
    return {
        "name": name,
        "nodes": nodes_list,
        "connections": _build_connections(nodes_list),
        "settings": {},
    }


def _build_connections(nodes):
    """Build node connections sequentially."""
    conn = {}
    for i, node in enumerate(nodes):
        if i < len(nodes) - 1:
            conn[node["name"]] = {
                "main": [[{"node": nodes[i + 1]["name"], "type": "main", "index": 0}]]
            }
    return conn


def generate_automation_workflow(a):
    """Generate a simple automation workflow."""
    webhook = make_webhook(a["webhook_path"])
    callback = make_callback(a["action"], extra_params=a.get("params", {}))
    fmt = make_format_response()
    return build_workflow_json(a["name"], a["webhook_path"], [webhook, callback, fmt])


def generate_ai_agent_workflow(a):
    """Generate a full AI agent workflow with memory + ollama."""
    webhook = make_webhook(a["webhook_path"])
    recall = make_callback("recall", query_template="={{ $json.body.message }}")
    world = make_callback("world")
    ollama = make_ollama_node(
        model="llama3.2",
        system_prompt=a["system_prompt"],
        user_template=(
            "Pergunta: {{ $json.body.message }}\n\n"
            "Memoria: {{ $('Kernel').first().json.results }}\n\n"
            "Contexto: {{ $('Kernel').last().json.state }}"
        ),
    )
    remember = make_callback(
        "remember",
        extra_params={
            "content": "={{ 'Pergunta: ' + $json.body.message + ' - Resposta: ' + $json.json.message.content }}",
            "kind": "conversa_ia",
        },
    )
    fmt = make_format_response()
    # Custom format for AI agent
    fmt["parameters"]["values"]["string"] = [
        {"name": "resposta", "value": "={{ $('Ollama').item.json.message.content }}"},
        {"name": "fontes", "value": "={{ $('Kernel').first().item.json.count + ' registros' }}"},
    ]
    return build_workflow_json(a["name"], a["webhook_path"], [webhook, recall, world, ollama, remember, fmt])


# ─── IMPORTAR ────────────────────────────────────────────

def import_workflow(wf_json):
    """Import a single workflow into n8n via API."""
    payload = json.dumps({
        "name": wf_json["name"],
        "nodes": wf_json["nodes"],
        "connections": wf_json["connections"],
        "settings": {},
    })
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/workflows",
        data=payload.encode("utf-8"),
        headers={
            "X-N8N-API-KEY": API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("id", "?")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        print(f"  ERRO [{e.code}]: {body}")
        return None


def main():
    print("=" * 60)
    print("GERADOR DE WORKFLOWS n8n - Sexta-Feira OS")
    print("=" * 60)

    total_ok = 0
    total_fail = 0

    # 1) Import 100 automations
    print("\n--- 100 AUTOMACOES ---")
    for a in AUTOMATIONS:
        print(f"Gerando: {a['name']}...", end=" ")
        wf = generate_automation_workflow(a)
        # Save to file
        fname = OUTPUT_DIR / f"auto-{a['id']}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
        # Import
        wid = import_workflow(wf)
        if wid:
            print(f"OK ID={wid}")
            total_ok += 1
        else:
            print("FAIL")
            total_fail += 1

    # 2) Import 50 AI agents
    print("\n--- 50 AI AGENTES ---")
    for a in AI_AGENTS:
        print(f"Gerando: {a['name']}...", end=" ")
        wf = generate_ai_agent_workflow(a)
        fname = OUTPUT_DIR / f"agent-{a['id']}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
        wid = import_workflow(wf)
        if wid:
            print(f"OK ID={wid}")
            total_ok += 1
        else:
            print("FAIL")
            total_fail += 1

    print("\n" + "=" * 60)
    print(f"RESUMO: {total_ok} importados, {total_fail} falhas")
    print(f"Arquivos salvos em: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
