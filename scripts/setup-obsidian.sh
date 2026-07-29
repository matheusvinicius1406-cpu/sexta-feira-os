#!/usr/bin/env bash
# =========================================================
# Sexta-Feira OS — configurar integração com vault Obsidian
# =========================================================
# Pergunta o caminho do vault Obsidian e escreve as
# configurações no .env (cria se não existir).
#
# Uso:
#   bash scripts/setup-obsidian.sh
# =========================================================
set -euo pipefail

# ── helpers ──────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}ℹ️  $1${NC}"; }
ok()    { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()   { echo -e "${RED}❌ $1${NC}"; }
header(){ echo -e "\n${BOLD}━━━ $1 ━━━${NC}\n"; }

# ── localização ──────────────────────────────────────────

cd "$(dirname "$0")/.."
ENV_FILE=".env"

# ── banner ───────────────────────────────────────────────

echo ""
echo -e "${BOLD}🧠  Sexta-Feira OS — Integração Obsidian${NC}"
echo "       Conecte seu vault ao cérebro"
echo ""

# ── 1) Caminho do vault ─────────────────────────────────

header "Caminho do Vault Obsidian"

echo "Digite o caminho absoluto para a pasta do seu vault Obsidian."
echo "Exemplos:"
echo "  /home/voce/Documents/MeuVault"
echo "  /Users/voce/Obsidian/principal"
echo "  D:\\Documentos\\Obsidian\\vault"
echo ""

DEFAULT_VAULT=""
if [ -d "$HOME/Documents/Obsidian" ]; then
    DEFAULT_VAULT="$HOME/Documents/Obsidian"
elif [ -d "$HOME/Obsidian" ]; then
    DEFAULT_VAULT="$HOME/Obsidian"
fi

read -r -p "$(echo -e "${CYAN}Caminho do vault${NC}${DEFAULT_VAULT:+ [$DEFAULT_VAULT]}: ")" VAULT_PATH
VAULT_PATH="${VAULT_PATH:-$DEFAULT_VAULT}"

# Validar
while [ -z "$VAULT_PATH" ] || [ ! -d "$VAULT_PATH" ]; do
    if [ -z "$VAULT_PATH" ]; then
        err "Caminho não pode ficar vazio."
    else
        err "Pasta não encontrada: $VAULT_PATH"
    fi
    echo ""
    read -r -p "$(echo -e "${CYAN}Caminho do vault${NC}: ")" VAULT_PATH
done

# Converter para caminho absoluto canónico
VAULT_PATH="$(cd "$VAULT_PATH" && pwd)"
ok "Vault encontrado: $VAULT_PATH"

# ── 2) Intervalo do watcher ──────────────────────────────

header "Watcher (sincronia automática)"

echo "A cada quantos segundos o watcher deve verificar"
echo "se houveram mudanças no vault?"
echo "  (entre 10 e 3600; padrão: 30)"
echo ""

read -r -p "$(echo -e "${CYAN}Intervalo (s)${NC} [30]: ")" WATCH_INTERVAL
WATCH_INTERVAL="${WATCH_INTERVAL:-30}"

# Validar
while ! [[ "$WATCH_INTERVAL" =~ ^[0-9]+$ ]] || [ "$WATCH_INTERVAL" -lt 10 ] || [ "$WATCH_INTERVAL" -gt 3600 ]; do
    warn "Digite um número entre 10 e 3600."
    read -r -p "$(echo -e "${CYAN}Intervalo (s)${NC} [30]: ")" WATCH_INTERVAL
    WATCH_INTERVAL="${WATCH_INTERVAL:-30}"
done

ok "Watcher a cada ${WATCH_INTERVAL}s"

# ── 3) Recall direto ─────────────────────────────────────

header "Recall Direto (notas recentes no contexto)"

echo "Durante uma conversa, o cérebro pode ler as notas .md"
echo "mais recentes do vault como contexto adicional."
echo ""
echo "Quantas notas no máximo? (0 = desligado; padrão: 10)"
echo ""

read -r -p "$(echo -e "${CYAN}Notas no contexto${NC} [10]: ")" RECALL_MAX
RECALL_MAX="${RECALL_MAX:-10}"

# Validar
while ! [[ "$RECALL_MAX" =~ ^[0-9]+$ ]] || [ "$RECALL_MAX" -lt 0 ] || [ "$RECALL_MAX" -gt 100 ]; do
    warn "Digite um número entre 0 e 100."
    read -r -p "$(echo -e "${CYAN}Notas no contexto${NC} [10]: ")" RECALL_MAX
    RECALL_MAX="${RECALL_MAX:-10}"
done

if [ "$RECALL_MAX" -eq 0 ]; then
    warn "Recall direto desligado."
else
    ok "Até $RECALL_MAX notas recentes no contexto"
fi

# ── 4) Escrever no .env ──────────────────────────────────

header "Escrevendo no $ENV_FILE"

# Cria .env se não existir
if [ ! -f "$ENV_FILE" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template "$ENV_FILE"
        ok "$ENV_FILE criado a partir do template"
    else
        touch "$ENV_FILE"
        warn "$ENV_FILE criado vazio (template não encontrado)"
    fi
fi

# Remove linhas existentes das chaves que vamos sobrescrever
# (usamos sed -i com backup no macOS vs Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_OPTS=(-i '')
else
    SED_OPTS=(-i)
fi

# Apagar linhas que começam com as chaves (preserva comentários acima)
for KEY in OBSIDIAN_VAULT_PATH OBSIDIAN_WATCH_INTERVAL OBSIDIAN_VAULT_RECALL_MAX_NOTES; do
    # macOS/BSD sed vs GNU sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "/^${KEY}=/d" "$ENV_FILE" 2>/dev/null || true
    else
        sed -i "/^${KEY}=/d" "$ENV_FILE" 2>/dev/null || true
    fi
done

# Adicionar as novas linhas (sempre no final do arquivo)
{
    echo ""
    echo "# --- Integração Obsidian (configurado por setup-obsidian.sh) ---"
    echo "OBSIDIAN_VAULT_PATH=$VAULT_PATH"
    echo "OBSIDIAN_WATCH_INTERVAL=$WATCH_INTERVAL"
    echo "OBSIDIAN_VAULT_RECALL_MAX_NOTES=$RECALL_MAX"
} >> "$ENV_FILE"

ok "Configurações escritas no $ENV_FILE"

# ── 5) Resumo ────────────────────────────────────────────

header "Resumo Final"

echo -e "  ${BOLD}Vault:${NC}            $VAULT_PATH"
echo -e "  ${BOLD}Watcher:${NC}          a cada ${WATCH_INTERVAL}s"
echo -e "  ${BOLD}Recall direto:${NC}    $RECALL_MAX notas"

echo ""
echo -e "${GREEN}✅ Integração Obsidian configurada!${NC}"
echo ""
# Tornar este script executável (útil na primeira execução)
if [ ! -x "$0" ]; then
    chmod +x "$0" 2>/dev/null || true
fi

echo "Reinicie o backend para ativar:"
echo "    # Ctrl+C no backend, depois:"
echo "    cd backend-core && source .venv/bin/activate"
echo "    python -m app.main"
echo ""
echo "Teste com:"
echo "    curl http://127.0.0.1:8000/api/v1/obsidian/status"
echo ""
