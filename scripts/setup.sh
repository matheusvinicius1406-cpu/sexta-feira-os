#!/usr/bin/env bash
# =========================================================
# Sexta-Feira OS — setup do kernel local e privado
# =========================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "🧠 Sexta-Feira OS — setup local"

# 1. Ollama (o cérebro local)
if ! command -v ollama >/dev/null 2>&1; then
  echo "➡️  Ollama não encontrado. Instale (roda 100% local):"
  echo "    Linux/Mac: curl -fsSL https://ollama.com/install.sh | sh"
  echo "    Windows:   https://ollama.com/download"
  echo "    Depois rode este script de novo."
  exit 1
fi

echo "⬇️  Baixando modelos locais (só desta vez)..."
# Dois pulls, não três: o cérebro conversa, usa ferramentas E enxerga. Só o
# modelo de embeddings vive à parte, porque virar texto em vetor é outro ofício.
ollama pull "${BRAIN_MODEL:-qwen3-vl:4b}"
ollama pull "${EMBEDDING_MODEL:-nomic-embed-text}"

# 2. Backend
echo "🐍 Preparando backend..."
cd backend-core
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
cd ..

# 3. .env
if [ ! -f .env ]; then
  cp .env.template .env
  echo "📝 .env criado a partir do template — EDITE OWNER_* e DEVICE_PAIRING_CODE."
fi

echo ""
echo "✅ Pronto. Para subir o kernel:"
echo "    cd backend-core && source .venv/bin/activate"
echo "    python -m app.main       # ou: uvicorn app.main:app"
echo "    Health: http://127.0.0.1:8000/api/v1/health"
