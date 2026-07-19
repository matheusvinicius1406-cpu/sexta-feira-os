"""Import the fixed super-sexta-workflow into n8n."""
import json
import urllib.request
import urllib.error
import os

API_KEY = os.environ.get("N8N_API_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyMDkwNGFkOC1iYjQ0LTQyOGEtYWVhZi1iZDA3OGIzMmNkOGIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNmQ4MjYzODktNzVmNy00Njg0LWEyNzYtZGUzZTY1MWU2Nzc2IiwiaWF0IjoxNzg0NDY0ODY5fQ.lP1NWKLlwx9_hVXN55rtRd_N79-DQWOEgTUASSih2RU"

BASE = "http://127.0.0.1:5678/api/v1/workflows"

def import_workflow(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)

    payload = json.dumps({
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": {},
    })

    req = urllib.request.Request(
        BASE,
        data=payload.encode("utf-8"),
        headers={
            "X-N8N-API-KEY": API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read().decode("utf-8"))
    print(f"OK Importado ID={d.get('id','?')} - {d.get('name','?')}")
    return d["id"]

if __name__ == "__main__":
    wid = import_workflow("scripts/n8n-workflows/super-sexta-workflow.json")
    print(f"\nSuper Workflow ID: {wid}")
    print(f"   Abra em: http://localhost:5678/workflow/{wid}")
