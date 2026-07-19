"""Fix $json.body references in Raciocinar (Ollama) node."""
import json

FILE = "scripts/n8n-workflows/super-sexta-workflow.json"

with open(FILE, "r", encoding="utf-8") as f:
    wf = json.load(f)

# Find the Raciocinar (Ollama) node
raciocinar = None
for node in wf["nodes"]:
    if node.get("id") == "ia-ollama":
        raciocinar = node
        break

if raciocinar is None:
    print("ERROR: Raciocinar node not found")
    exit(1)

# Get the jsonBody string
raw_body = raciocinar["parameters"]["jsonBody"]
print("BEFORE:", raw_body[:200], "...")

# Fix the expressions
raw_body = raw_body.replace(
    "{{ $json.body.mensagem || $json.body.message }}",
    "{{ $(\\\"Entrada\\\").item.json.body.mensagem || $(\\\"Entrada\\\").item.json.body.message }}"
)
raw_body = raw_body.replace(
    "{{ $json.body.papel || 'assistente geral' }}",
    "{{ $(\\\"Entrada\\\").item.json.body.papel || 'assistente geral' }}"
)

raciocinar["parameters"]["jsonBody"] = raw_body
print("AFTER:", raw_body[:200])

# Write back
with open(FILE, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)

print("\nOK - file updated")
