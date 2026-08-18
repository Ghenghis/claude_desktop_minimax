# Repair the claude-minimax-v2 gateway and Claude Desktop wiring.
# Idempotent: safe to run repeatedly.  It only touches HKCU and a per-process env.
[CmdletBinding()]
param(
    [int]$PreferredPort = 48217
)

$ErrorActionPreference = 'Stop'

# 1. Load the key (fails early with a helpful message if missing).
$keyPath = 'G:\private\minimax_key.txt'
$envPath = 'G:\private\.env'
if (-not (Test-Path $keyPath) -and -not (Test-Path $envPath)) {
    throw "MiniMax key not found. Please place your API key in $keyPath or set MINIMAX_API_KEY in $envPath"
}

# 2. Stop any running gateway.
$stopScript = Join-Path $PSScriptRoot 'Stop-MinimaxGateway.ps1'
if (Test-Path $stopScript) {
    & $stopScript -Port $PreferredPort -ErrorAction SilentlyContinue
}

# 3. Remove stale port file.
$githubRoot = Split-Path -Parent $PSScriptRoot
$gatewayRoot = Join-Path $githubRoot 'claude-minimax-v2'
$portFile = Join-Path $gatewayRoot '.port'
if (Test-Path $portFile) { Remove-Item $portFile -Force }

# 4. Validate Python files compile before trying to start.
$pyFiles = Get-ChildItem -Path $gatewayRoot -Recurse -File -Filter '*.py'
foreach ($file in $pyFiles) {
    python -m py_compile $file.FullName
}
Write-Host "All Python files compile." -ForegroundColor Green

# 5. Re-start and re-wire.
$startScript = Join-Path $PSScriptRoot 'Start-ClaudeMinimaxV2.ps1'
& $startScript -PreferredPort $PreferredPort

Write-Host "Repair complete. Restart Claude Desktop if it is already open." -ForegroundColor Green
