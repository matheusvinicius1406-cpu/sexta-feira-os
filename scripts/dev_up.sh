#!/usr/bin/env bash
# =========================================================
# Sexta-Feira OS — sobe kernel + HUD juntos, um comando só.
#
# Não é um "start em paralelo e torce": cada etapa confere a anterior antes
# de seguir (Ollama respondendo, .env existindo, /api/v1/health respondendo
# de verdade), e se o kernel morrer no boot o script para e mostra o log —
# em vez de subir o HUD contra um backend morto e dar erro só depois.
# =========================================================
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1/health"
BACKEND_LOG="$ROOT/backend-core/.dev-backend.log"
FRONTEND_LOG="$ROOT/jarvis-ui/.dev-frontend.log"

echo "🧠 Sexta-Feira OS — subindo kernel + HUD"
echo ""

# 1. Ollama precisa estar de pé ANTES do kernel — o boot só avisa se faltar
#    modelo, não sobe o Ollama por você.
if ! curl -sf -m 3 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  echo "❌ Ollama não responde em 127.0.0.1:11434. Abra o Ollama e rode este script de novo."
  exit 1
fi
echo "✅ Ollama respondendo"

# 2. .env precisa existir — sem ele não há dono, e nada autentica.
if [ ! -f "$ROOT/.env" ]; then
  echo "❌ .env não encontrado na raiz. Copie de .env.template, ajuste OWNER_* e rode de novo."
  exit 1
fi
echo "✅ .env presente"

# 2b. Limpa processos travados de uma rodada anterior. Parar o script (Ctrl+C
#     ou matar o wrapper) nem sempre mata o processo Python/Node filho no
#     Windows/Git Bash — ele fica de pé, segurando a porta, e a PRÓXIMA subida
#     falha com "port in use" ou (pior) o vite pula de porta e o HUD abre no
#     endereço errado. Mata só quem estiver especificamente nestas portas.
GRPC_PORT="${GRPC_PORT:-50051}"
for p in "$BACKEND_PORT" "$GRPC_PORT" 3000; do
  powershell -NoProfile -Command \
    "Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | \
     ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" \
    >/dev/null 2>&1
done

# 3. Backend — em segundo plano, log num arquivo para poder diagnosticar
#    sem misturar com a saída do frontend.
echo ""
echo "🐍 Kernel subindo (log: backend-core/.dev-backend.log)..."
# O pulse (a iniciativa do agente) é uma escolha do dev, não da máquina: uma
# AGENT_PULSE_ENABLED=false no ambiente do usuário não pode desligar a
# autonomia de propósito. Pina aqui como o conftest pina nos testes.
export AGENT_PULSE_ENABLED="${AGENT_PULSE_ENABLED:-true}"
(
  cd "$ROOT/backend-core"
  exec .venv/Scripts/python -m app.main
) > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

FRONTEND_PID=""
cleanup() {
  echo ""
  echo "🛑 Encerrando kernel + HUD..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# Espera o kernel responder DE VERDADE (health real), não um sleep no escuro.
# Se o processo morrer antes de responder, para e mostra por quê — subir o
# HUD contra isso só trocaria um erro claro agora por um confuso depois.
echo -n "   aguardando /api/v1/health"
READY=0
for _ in $(seq 1 90); do
  if curl -sf -m 2 "$HEALTH_URL" >/dev/null 2>&1; then
    READY=1
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "❌ O kernel morreu durante o boot. Últimas linhas de $BACKEND_LOG:"
    tail -n 30 "$BACKEND_LOG"
    exit 1
  fi
  echo -n "."
  sleep 1
done
echo ""
if [ "$READY" -ne 1 ]; then
  echo "❌ Kernel não respondeu em 90s. Últimas linhas de $BACKEND_LOG:"
  tail -n 30 "$BACKEND_LOG"
  exit 1
fi
echo "✅ Kernel pronto — $HEALTH_URL"

# 4. Frontend — só depois do backend estar de pé de verdade.
echo ""
echo "🖥️  HUD subindo (log: jarvis-ui/.dev-frontend.log)..."
(
  cd "$ROOT/jarvis-ui"
  exec npm run dev
) > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# Vite anuncia a própria URL no log; espera aparecer em vez de adivinhar a
# porta (o vite pula pra 3001+ sozinho se 3000 já estiver ocupada). O log tem
# cores ANSI no meio dos dígitos da porta ("localhost:\e[1m3001\e[22m/"), então
# os códigos saem ANTES do grep — sem isso o padrão nunca casava e o script
# sempre caía no fallback, que podia apontar pra porta errada.
FRONTEND_URL=""
for _ in $(seq 1 30); do
  FRONTEND_URL=$(sed -r 's/\x1b\[[0-9;]*[a-zA-Z]//g' "$FRONTEND_LOG" 2>/dev/null | grep -oE 'http://localhost:[0-9]+' | head -n1)
  [ -n "$FRONTEND_URL" ] && break
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "❌ O HUD morreu ao subir. Últimas linhas de $FRONTEND_LOG:"
    tail -n 30 "$FRONTEND_LOG"
    exit 1
  fi
  sleep 1
done
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
echo "✅ HUD pronto — $FRONTEND_URL"

echo ""
echo "════════════════════════════════════════════"
echo " Kernel:  $HEALTH_URL"
echo " HUD:     $FRONTEND_URL"
echo "════════════════════════════════════════════"
echo ""
echo "Ctrl+C encerra os dois."

wait "$BACKEND_PID" "$FRONTEND_PID"
