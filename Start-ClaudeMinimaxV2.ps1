# Start the claude-minimax-v2 gateway on an available port and wire Claude Desktop.
# This is the one-touch setup for any Windows 11 PC; just run it, then restart Claude Desktop.

[CmdletBinding()]
param(
    [int]$PreferredPort = 48217
)

$ErrorActionPreference = 'Stop'

# Load the key into this process only.
. $PSScriptRoot\Load-MinimaxKey.ps1

$githubRoot = Split-Path -Parent $PSScriptRoot
$gatewayRoot = Join-Path $githubRoot 'claude-minimax-v2'
$portFile = Join-Path $gatewayRoot '.port'

# Stop any already-running gateway so we don't get port conflicts.
$null = & $PSScriptRoot\Stop-MinimaxGateway.ps1 -Port $PreferredPort

if (-not (Test-Path $gatewayRoot -PathType Container)) {
    throw "claude-minimax-v2 gateway not found next to this script: $gatewayRoot"
}

# Pick a free port and clean up any stale port file.
if (Test-Path $portFile) { Remove-Item $portFile -Force }

$port = & python (Join-Path $gatewayRoot 'port_util.py') "--preferred" $PreferredPort

if ($port -ne $PreferredPort) {
    Write-Host "Port $PreferredPort was busy, so the gateway is using port $port instead." -ForegroundColor Yellow
    Write-Host "If you wanted port $PreferredPort, close the other program and re-run this script." -ForegroundColor Cyan
}

# Resolve Python and start the gateway in the background.
$python = (Get-Command python -ErrorAction Stop).Source
$env:CLAUDE_MINIMAX_PROXY_PORT = $port

$proc = Start-Process -FilePath $python -ArgumentList '-m', 'gateway.server' -WorkingDirectory $gatewayRoot -PassThru -WindowStyle Hidden

# Wait for the gateway to write its actual port.
$waited = 0
while ($waited -lt 30) {
    Start-Sleep -Milliseconds 500
    $waited += 0.5
    if (Test-Path $portFile) {
        $actual = [int](Get-Content -Path $portFile -TotalCount 1)
        if ($actual -eq $port) { break }
    }
}

if (-not (Test-Path $portFile) -or [int](Get-Content -Path $portFile -TotalCount 1) -ne $port) {
    Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
    throw "Gateway did not start on port $port within 30s"
}

# Wire Claude Desktop.
& $PSScriptRoot\Set-ClaudeDesktopGateway.ps1 -ProxyPort $port

Write-Host "Gateway running on http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "Test UI: http://127.0.0.1:$port/ui" -ForegroundColor Cyan
Write-Host "Restart Claude Desktop now." -ForegroundColor Yellow
