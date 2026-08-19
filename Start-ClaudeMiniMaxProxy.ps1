# Load the MiniMax API key from G:\private\.env into THIS process only.
# Load-MinimaxKey.ps1 never prints, returns, or persists the value.
. $PSScriptRoot\Load-MinimaxKey.ps1

$port = 48217
$proxy = Join-Path $PSScriptRoot "claude-minimax-proxy.py"

$env:CLAUDE_MINIMAX_PROXY_PORT = $port
$env:MINIMAX_ENV_FILE = 'G:\private\.env'
Write-Host "Starting Claude <-> MiniMax proxy on http://127.0.0.1:$port/anthropic" -ForegroundColor Green
Write-Host "Key source: $env:MINIMAX_ENV_FILE (not echoed)" -ForegroundColor DarkGray
Write-Host "Keep this window open. Press Ctrl+C here to stop the proxy." -ForegroundColor Yellow

python $proxy
