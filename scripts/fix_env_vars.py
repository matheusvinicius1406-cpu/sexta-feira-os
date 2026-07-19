"""Replace $env.N8N_CALLBACK_SECRET, $env.KERNEL_URL, $env.OLLAMA_URL
with literal values. n8n Community Edition doesn't support $env (paid feature)."""
import json
import re

FILE = "scripts/n8n-workflows/super-sexta-workflow.json"
SECRET = "Si3hkdlTApTEPcIbo2Giqly1KWU9gMtmjruu00yKymo"
KERNEL_URL = "http://host.docker.internal:8000"
OLLAMA_URL = "http://host.docker.internal:11434"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

original = content

# Replace $env.N8N_CALLBACK_SECRET in header values
content = content.replace(
    "={{ $env.N8N_CALLBACK_SECRET }}",
    SECRET
)

# Replace $env.KERNEL_URL || 'fallback' with just the fallback URL
content = content.replace(
    "$env.KERNEL_URL || '" + KERNEL_URL + "'",
    "'" + KERNEL_URL + "'"
)

# Replace $env.OLLAMA_URL || 'fallback' with just the fallback URL
content = content.replace(
    "$env.OLLAMA_URL || '" + OLLAMA_URL + "'",
    "'" + OLLAMA_URL + "'"
)

changes = 0
if content != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)
    changes = sum([
        content.count(SECRET),
        content.count(KERNEL_URL) - original.count(KERNEL_URL),
        content.count(OLLAMA_URL) - original.count(OLLAMA_URL),
    ])
    print(f"OK - workflow atualizado (secret + urls hardcoded)")
else:
    print("INFO - nenhuma mudanca necessaria")

# Count final state
print(f"Secret refs: {content.count(SECRET)}")
print(f"Kernel url: {content.count(KERNEL_URL)}")
print(f"Ollama url: {content.count(OLLAMA_URL)}")
