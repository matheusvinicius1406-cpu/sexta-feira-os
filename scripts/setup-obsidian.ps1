<#
.SYNOPSIS
    Sexta-Feira OS — Configurar integração com vault Obsidian
.DESCRIPTION
    Pergunta o caminho do vault Obsidian e escreve as configurações
    no .env (cria se não existir).
.EXAMPLE
    .\scripts\setup-obsidian.ps1
#>

# ── helpers ──────────────────────────────────────────────

function Write-Info   { Write-Host "ℹ️  $($args[0])" -ForegroundColor Cyan }
function Write-Ok     { Write-Host "✅ $($args[0])" -ForegroundColor Green }
function Write-Warn   { Write-Host "⚠️  $($args[0])" -ForegroundColor Yellow }
function Write-Err    { Write-Host "❌ $($args[0])" -ForegroundColor Red }
function Write-Header { Write-Host "`n━━━ $($args[0]) ━━━`n" -ForegroundColor White }

# ── localização ──────────────────────────────────────────

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\.."
Set-Location $ProjectRoot

$EnvFile = ".env"

# ── banner ───────────────────────────────────────────────

Write-Host "`n🧠  Sexta-Feira OS — Integração Obsidian" -ForegroundColor White
Write-Host "       Conecte seu vault ao cérebro`n"

# ── 1) Caminho do vault ─────────────────────────────────

Write-Header "Caminho do Vault Obsidian"

Write-Host "Digite o caminho absoluto para a pasta do seu vault Obsidian."
Write-Host "Exemplos:"
Write-Host "  C:\Users\voce\Documents\Obsidian\MeuVault"
Write-Host "  D:\Documentos\Obsidian\principal"
Write-Host ""

# Detetar caminhos comuns
$DefaultVault = ""
$CommonPaths = @(
    "$env:USERPROFILE\Documents\Obsidian",
    "$env:USERPROFILE\Obsidian",
    "$env:USERPROFILE\OneDrive\Documentos\Obsidian"
)
foreach ($p in $CommonPaths) {
    if (Test-Path $p -PathType Container) {
        $DefaultVault = $p
        break
    }
}

$prompt = "Caminho do vault"
if ($DefaultVault) {
    $prompt += " [$DefaultVault]"
}
$prompt += ": "

$VaultPath = Read-Host $prompt
if (-not $VaultPath) { $VaultPath = $DefaultVault }

# Validar
while (-not $VaultPath -or -not (Test-Path $VaultPath -PathType Container)) {
    if (-not $VaultPath) {
        Write-Err "Caminho não pode ficar vazio."
    } else {
        Write-Err "Pasta não encontrada: $VaultPath"
    }
    Write-Host ""
    $VaultPath = Read-Host "Caminho do vault"
}

# Converter para caminho absoluto canónico
$VaultPath = (Resolve-Path $VaultPath).Path
Write-Ok "Vault encontrado: $VaultPath"

# ── 2) Intervalo do watcher ──────────────────────────────

Write-Header "Watcher (sincronia automática)"

Write-Host "A cada quantos segundos o watcher deve verificar"
Write-Host "se houveram mudanças no vault?"
Write-Host "  (entre 10 e 3600; padrão: 30)"
Write-Host ""

$WatchInterval = Read-Host "Intervalo (s) [30]"
if (-not $WatchInterval) { $WatchInterval = "30" }

# Validar
while (-not ($WatchInterval -match '^\d+$') -or [int]$WatchInterval -lt 10 -or [int]$WatchInterval -gt 3600) {
    Write-Warn "Digite um número entre 10 e 3600."
    $WatchInterval = Read-Host "Intervalo (s) [30]"
    if (-not $WatchInterval) { $WatchInterval = "30" }
}

Write-Ok "Watcher a cada ${WatchInterval}s"

# ── 3) Recall direto ─────────────────────────────────────

Write-Header "Recall Direto (notas recentes no contexto)"

Write-Host "Durante uma conversa, o cérebro pode ler as notas .md"
Write-Host "mais recentes do vault como contexto adicional."
Write-Host ""
Write-Host "Quantas notas no máximo? (0 = desligado; padrão: 10)"
Write-Host ""

$RecallMax = Read-Host "Notas no contexto [10]"
if (-not $RecallMax) { $RecallMax = "10" }

# Validar
while (-not ($RecallMax -match '^\d+$') -or [int]$RecallMax -lt 0 -or [int]$RecallMax -gt 100) {
    Write-Warn "Digite um número entre 0 e 100."
    $RecallMax = Read-Host "Notas no contexto [10]"
    if (-not $RecallMax) { $RecallMax = "10" }
}

if ([int]$RecallMax -eq 0) {
    Write-Warn "Recall direto desligado."
} else {
    Write-Ok "Até $RecallMax notas recentes no contexto"
}

# ── 4) Escrever no .env ──────────────────────────────────

Write-Header "Escrevendo no $EnvFile"

# Cria .env se não existir
if (-not (Test-Path $EnvFile -PathType Leaf)) {
    if (Test-Path ".env.template" -PathType Leaf) {
        Copy-Item ".env.template" $EnvFile
        Write-Ok "$EnvFile criado a partir do template"
    } else {
        New-Item -Path $EnvFile -ItemType File -Force | Out-Null
        Write-Warn "$EnvFile criado vazio (template não encontrado)"
    }
}

# Ler conteúdo atual, remover linhas das chaves que vamos sobrescrever,
# e adicionar as novas linhas no final.
$KeysToReplace = @(
    "OBSIDIAN_VAULT_PATH",
    "OBSIDIAN_WATCH_INTERVAL",
    "OBSIDIAN_VAULT_RECALL_MAX_NOTES"
)

$CurrentContent = Get-Content $EnvFile -Raw -ErrorAction SilentlyContinue
if (-not $CurrentContent) { $CurrentContent = "" }

# Filtrar linhas que começam com as chaves (regex: ^KEY=)
$Lines = $CurrentContent -split "`r?`n"
$FilteredLines = @()
foreach ($Line in $Lines) {
    $ShouldKeep = $true
    foreach ($Key in $KeysToReplace) {
        if ($Line -match "^$Key=") {
            $ShouldKeep = $false
            break
        }
    }
    if ($ShouldKeep) {
        $FilteredLines += $Line
    }
}

# Preserva linhas vazias para manter a formatação visual do .env
$NewContent = @"
$($FilteredLines -join "`r`n")

# --- Integração Obsidian (configurado por setup-obsidian.ps1) ---
OBSIDIAN_VAULT_PATH=$VaultPath
OBSIDIAN_WATCH_INTERVAL=$WatchInterval
OBSIDIAN_VAULT_RECALL_MAX_NOTES=$RecallMax
"@

# Garantir quebra de linha no final
$NewContent = $NewContent.TrimEnd() + "`r`n"

# Escrever
[System.IO.File]::WriteAllText(
    (Resolve-Path $EnvFile).Path,
    $NewContent,
    [System.Text.UTF8Encoding]::new($false)  # sem BOM
)

Write-Ok "Configurações escritas no $EnvFile"

# ── 5) Resumo ────────────────────────────────────────────

Write-Header "Resumo Final"

Write-Host "  Vault:            $VaultPath" -ForegroundColor White
Write-Host "  Watcher:          a cada ${WatchInterval}s" -ForegroundColor White
Write-Host "  Recall direto:    $RecallMax notas" -ForegroundColor White

Write-Host ""
Write-Host "✅ Integração Obsidian configurada!" -ForegroundColor Green
Write-Host ""
Write-Host "Reinicie o backend para ativar:"
Write-Host "    # Ctrl+C no backend, depois:"
Write-Host "    cd backend-core"
Write-Host "    python -m app.main"
Write-Host ""
Write-Host "Teste com:"
Write-Host "    curl http://127.0.0.1:8000/api/v1/obsidian/status"
Write-Host ""
