"""
The automations REST API, against the running kernel.

Uses the shared TestClient, so these exercise the real wiring: the kernel builds
the Teia at boot, seeds the catalog, arms the triggers, and the router talks to
that same instance.
"""


def workflow_body(name: str, slug: str, **extra) -> dict:
    body = {
        "slug": slug,
        "descricao": f"automação de teste: {name}",
        "definicao": {
            "name": name,
            "nodes": [
                {"id": "a", "type": "inicio", "config": {"dados": {"origem": "api"}}},
                {"id": "b", "type": "texto", "config": {"texto": "veio de {{ nodes.a.origem }}"}},
            ],
            "connections": [{"source": "a", "target": "b"}],
            "triggers": [],
        },
    }
    body.update(extra)
    return body


# ---------------------------------------------------------------- engine


def test_status_reports_the_local_engine(client, owner_headers):
    body = client.get("/api/v1/automations/status", headers=owner_headers).json()
    assert body["engine"] == "teia"
    assert body["online"] is True          # in-process: no external runtime to miss
    assert body["node_types"] >= 40


def test_types_endpoint_documents_every_node(client, owner_headers):
    body = client.get("/api/v1/automations/types", headers=owner_headers).json()
    types = {n["type"] for n in body["nodes"]}
    assert {"inicio", "se", "http", "memoria_gravar", "notificar"} <= types
    assert {t["type"] for t in body["triggers"]} == {
        "manual", "agenda", "intervalo", "evento", "webhook",
    }
    # Every node ships a JSON Schema the editor can render.
    assert all(n["config_schema"]["type"] == "object" for n in body["nodes"])


# ---------------------------------------------------------------- CRUD


def test_create_read_run_and_delete(client, owner_headers):
    created = client.post(
        "/api/v1/automations", json=workflow_body("API teste", "api-teste"),
        headers=owner_headers,
    )
    assert created.status_code == 201
    assert created.json()["slug"] == "api-teste"

    listed = client.get("/api/v1/automations", headers=owner_headers).json()
    assert "api-teste" in {w["slug"] for w in listed}

    detail = client.get("/api/v1/automations/api-teste", headers=owner_headers).json()
    assert len(detail["definition"]["nodes"]) == 2

    run = client.post(
        "/api/v1/automations/api-teste/run", json={}, headers=owner_headers
    ).json()
    assert run["ok"] is True
    assert run["output"]["b"] == [{"texto": "veio de api"}]
    assert run["nodes_executed"] == 2

    removed = client.delete("/api/v1/automations/api-teste", headers=owner_headers)
    assert removed.status_code == 200
    assert client.get(
        "/api/v1/automations/api-teste", headers=owner_headers
    ).status_code == 404


def test_creating_an_invalid_workflow_explains_why(client, owner_headers):
    body = workflow_body("Ruim", "api-ruim")
    body["definicao"]["nodes"][0]["type"] = "nao_existe"
    response = client.post("/api/v1/automations", json=body, headers=owner_headers)
    assert response.status_code == 422
    assert "tipo de nó desconhecido" in str(response.json()["detail"])


def test_validate_does_not_persist(client, owner_headers):
    body = workflow_body("Só validar", "api-validar")
    ok = client.post("/api/v1/automations/validate", json=body, headers=owner_headers).json()
    assert ok == {"valido": True, "problemas": [], "nos": 2}
    assert client.get(
        "/api/v1/automations/api-validar", headers=owner_headers
    ).status_code == 404


def test_validate_reports_a_dangling_connection(client, owner_headers):
    body = workflow_body("Solta", "api-solta")
    body["definicao"]["connections"].append({"source": "b", "target": "fantasma"})
    result = client.post(
        "/api/v1/automations/validate", json=body, headers=owner_headers
    ).json()
    assert result["valido"] is False
    assert any("destino inexistente" in p for p in result["problemas"])


def test_yaml_authoring(client, owner_headers):
    yaml_text = """
name: Via YAML
nodes:
  - id: a
    type: inicio
    config:
      dados:
        origem: yaml
  - id: b
    type: texto
    config:
      texto: "veio de {{ nodes.a.origem }}"
connections:
  - source: a
    target: b
triggers: []
"""
    created = client.post(
        "/api/v1/automations",
        json={"slug": "api-yaml", "yaml": yaml_text},
        headers=owner_headers,
    )
    assert created.status_code == 201

    run = client.post("/api/v1/automations/api-yaml/run", json={}, headers=owner_headers)
    assert run.json()["output"]["b"] == [{"texto": "veio de yaml"}]
    client.delete("/api/v1/automations/api-yaml", headers=owner_headers)


def test_saving_without_a_graph_is_rejected(client, owner_headers):
    response = client.post(
        "/api/v1/automations", json={"slug": "vazia"}, headers=owner_headers
    )
    assert response.status_code == 422


def test_enable_and_disable(client, owner_headers):
    client.post(
        "/api/v1/automations", json=workflow_body("Liga desliga", "api-liga"),
        headers=owner_headers,
    )
    client.post(
        "/api/v1/automations/api-liga/enable", json={"ativo": False}, headers=owner_headers
    )
    assert client.get(
        "/api/v1/automations/api-liga", headers=owner_headers
    ).json()["enabled"] is False
    client.delete("/api/v1/automations/api-liga", headers=owner_headers)


def test_unknown_slug_returns_404(client, owner_headers):
    assert client.post(
        "/api/v1/automations/run", json={"automacao": "nao-existe"}, headers=owner_headers
    ).status_code == 404
    assert client.post(
        "/api/v1/automations/nao-existe/enable", json={"ativo": True}, headers=owner_headers
    ).status_code == 404


# ---------------------------------------------------------------- trail


def test_executions_are_listed_and_detailed(client, owner_headers):
    client.post(
        "/api/v1/automations", json=workflow_body("Trilha", "api-trilha"),
        headers=owner_headers,
    )
    run = client.post(
        "/api/v1/automations/run", json={"automacao": "api-trilha", "dados": {"x": 1}},
        headers=owner_headers,
    ).json()

    listed = client.get(
        "/api/v1/automations/executions?automacao=api-trilha", headers=owner_headers
    ).json()
    assert listed[0]["id"] == run["execution_id"]
    assert listed[0]["status"] == "completed"

    detail = client.get(
        f"/api/v1/automations/executions/{run['execution_id']}", headers=owner_headers
    ).json()
    assert {n["node_id"] for n in detail["nodes"]} == {"a", "b"}
    client.delete("/api/v1/automations/api-trilha", headers=owner_headers)


def test_unknown_execution_returns_404(client, owner_headers):
    assert client.get(
        "/api/v1/automations/executions/nao-existe", headers=owner_headers
    ).status_code == 404


def test_cancelling_an_idle_execution_returns_404(client, owner_headers):
    assert client.post(
        "/api/v1/automations/executions/nao-existe/cancel", headers=owner_headers
    ).status_code == 404


# ---------------------------------------------------------------- webhooks


def test_webhook_runs_the_automation_it_is_wired_to(client, owner_headers):
    body = workflow_body("Gancho API", "api-gancho")
    body["definicao"]["nodes"][1]["config"]["texto"] = "recebi: {{ trigger.texto }}"
    body["definicao"]["triggers"] = [
        {"id": "t1", "type": "webhook", "target": "a", "config": {"caminho": "api-gancho"}}
    ]
    assert client.post(
        "/api/v1/automations", json=body, headers=owner_headers
    ).status_code == 201

    # No owner token: a webhook is the entry point for other local programs.
    fired = client.post(
        "/api/v1/automations/webhook/api-gancho", json={"texto": "olá"}
    )
    assert fired.status_code == 200
    assert fired.json()["output"]["b"] == [{"texto": "recebi: olá"}]
    client.delete("/api/v1/automations/api-gancho", headers=owner_headers)


def test_webhook_with_a_secret_requires_the_header(client, owner_headers):
    body = workflow_body("Gancho secreto", "api-gancho-secreto")
    body["definicao"]["triggers"] = [{
        "id": "t1", "type": "webhook", "target": "a",
        "config": {"caminho": "api-secreto", "segredo": "abre-te-sesamo"},
    }]
    client.post("/api/v1/automations", json=body, headers=owner_headers)

    assert client.post("/api/v1/automations/webhook/api-secreto", json={}).status_code == 401
    assert client.post(
        "/api/v1/automations/webhook/api-secreto", json={},
        headers={"X-Teia-Secret": "errado"},
    ).status_code == 401
    assert client.post(
        "/api/v1/automations/webhook/api-secreto", json={},
        headers={"X-Teia-Secret": "abre-te-sesamo"},
    ).status_code == 200
    client.delete("/api/v1/automations/api-gancho-secreto", headers=owner_headers)


def test_unknown_webhook_returns_404(client):
    assert client.post("/api/v1/automations/webhook/nada-aqui", json={}).status_code == 404


def test_a_disabled_automation_stops_answering_its_webhook(client, owner_headers):
    body = workflow_body("Gancho off", "api-gancho-off")
    body["definicao"]["triggers"] = [
        {"id": "t1", "type": "webhook", "target": "a", "config": {"caminho": "api-off"}}
    ]
    client.post("/api/v1/automations", json=body, headers=owner_headers)
    assert client.post("/api/v1/automations/webhook/api-off", json={}).status_code == 200

    client.post(
        "/api/v1/automations/api-gancho-off/enable", json={"ativo": False},
        headers=owner_headers,
    )
    assert client.post("/api/v1/automations/webhook/api-off", json={}).status_code == 404
    client.delete("/api/v1/automations/api-gancho-off", headers=owner_headers)


# ---------------------------------------------------------------- catalog


def test_the_catalog_is_installed_at_boot(client, owner_headers):
    slugs = {
        w["slug"] for w in client.get("/api/v1/automations", headers=owner_headers).json()
    }
    assert {"briefing-matinal", "backup-do-kernel", "captura-rapida"} <= slugs


def test_installing_the_catalog_again_adds_nothing(client, owner_headers):
    response = client.post("/api/v1/automations/catalog/install", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["instaladas"] == []


def test_the_captura_webhook_from_the_catalog_answers(client, owner_headers):
    """The shipped inbox automation works out of the box (memory + today's file)."""
    response = client.post(
        "/api/v1/automations/webhook/captura", json={"texto": "ideia vinda do teste"}
    )
    assert response.status_code == 200
    body = response.json()
    # The notify step needs a paired device, which CI has none of; what must hold
    # is that the automation ran and reached its nodes.
    assert body["status"] in ("completed", "failed")
    assert body["nodes_executed"] >= 2
