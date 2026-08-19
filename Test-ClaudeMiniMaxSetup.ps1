# Verify the Claude Desktop <-> MiniMax proxy setup end-to-end.
. $PSScriptRoot\minimax_env.ps1

$port = 48217
$proxyUrl = "http://127.0.0.1:$port/anthropic"
$regPath = "HKCU:\SOFTWARE\Policies\Claude"

$ok = $true

function Check($label, $script) {
    try {
        $result = & $script
        Write-Host "[OK] $label" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "[FAIL] $label : $_" -ForegroundColor Red
        return $false
    }
}

$ok = (Check "Registry has gateway provider" {
    $p = Get-ItemProperty -Path $regPath -Name "inferenceProvider" -ErrorAction Stop
    if ($p.inferenceProvider -ne "gateway") { throw "inferenceProvider is $($p.inferenceProvider)" }
}) -and $ok

$ok = (Check "Registry points at local proxy" {
    $p = Get-ItemProperty -Path $regPath -Name "inferenceGatewayBaseUrl" -ErrorAction Stop
    if ($p.inferenceGatewayBaseUrl -notlike "*127.0.0.1:$port*") { throw "baseUrl is $($p.inferenceGatewayBaseUrl)" }
}) -and $ok

$ok = (Check "Registry uses Anthropic-looking model name" {
    $p = Get-ItemProperty -Path $regPath -Name "inferenceModels" -ErrorAction Stop
    if ($p.inferenceModels -notlike "*claude-sonnet-4-5*") { throw "inferenceModels is $($p.inferenceModels)" }
    if ($p.inferenceModels -like "*MiniMax-M3*") { throw "inferenceModels still contains raw MiniMax-M3" }
}) -and $ok

$ok = (Check "Proxy is listening on port $port" {
    $conn = Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet
    if (-not $conn) { throw "port $port not reachable" }
}) -and $ok

$ok = (Check "Proxy /v1/models returns Anthropic-shaped list" {
    $resp = Invoke-RestMethod -Uri "$proxyUrl/v1/models?limit=1000" -Method GET -TimeoutSec 10
    if ($resp.data.Count -lt 1) { throw "empty model list" }
    if ($resp.data[0].id -ne "claude-sonnet-4-5") { throw "first model id is $($resp.data[0].id)" }
}) -and $ok

$ok = (Check "Proxy forwards message to MiniMax and returns MiniMax-M3" {
    $body = @{
        model = "claude-sonnet-4-5"
        max_tokens = 5
        messages = @(@{ role = "user"; content = "hi" })
    } | ConvertTo-Json -Depth 5
    $headers = @{ "X-Api-Key" = $env:ANTHROPIC_AUTH_TOKEN; "Content-Type" = "application/json" }
    $resp = Invoke-RestMethod -Uri "$proxyUrl/v1/messages" -Method POST -Body $body -Headers $headers -TimeoutSec 60
    if ($resp.model -ne "MiniMax-M3") { throw "upstream model is $($resp.model)" }
    if (-not $resp.content) { throw "no content in response" }
}) -and $ok

$ok = (Check "Claude Desktop log shows healthy 3P config" {
    $log = "$env:LOCALAPPDATA\Claude-3p\logs\main.log"
    if (-not (Test-Path $log)) { throw "main.log not found" }
    $tail = Get-Content $log -Tail 200 -ErrorAction Stop
    $matches = $tail | Select-String "ConfigHealth recomputed"
    if (-not $matches) { throw "no ConfigHealth line in recent log" }
    $last = $matches | Select-Object -Last 1
    if ($last -notmatch "healthy") { throw "last ConfigHealth was not healthy: $last" }
}) -and $ok

if ($ok) {
    Write-Host "`nAll checks passed. Claude Desktop should work once restarted with the proxy running." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome checks failed. Fix the issues above before restarting Claude Desktop." -ForegroundColor Red
    exit 1
}
