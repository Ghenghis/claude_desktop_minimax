[CmdletBinding()]
param(
    [switch]$Fix,
    [string]$LogFile = 'C:\Users\Admin\claude-codex-devin\logs\minimax-stack-health.log'
)

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Path (Split-Path $LogFile) -Force | Out-Null
$results = [System.Collections.Generic.List[object]]::new()

function Add-Result([string]$Check, [bool]$Pass, [string]$Detail) {
    $results.Add([pscustomobject]@{ Check = $Check; Status = $(if ($Pass) { 'PASS' } else { 'FAIL' }); Detail = $Detail })
}

$token = (Get-Content -LiteralPath 'C:\private\.proxy-token' -Raw -ErrorAction SilentlyContinue)
if ($token) { $token = $token.Trim() }
Add-Result 'Secrets present' ([bool]$token -and (Test-Path 'C:\private\.env')) 'C:\private\.env + .proxy-token'

# --- Windows services -------------------------------------------------------
foreach ($svc in @('claude-minimax-proxy', 'api2codex-minimax')) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    $running = $s -and $s.Status -eq 'Running'
    if (-not $running -and $Fix) {
        Start-Service -Name $svc -ErrorAction SilentlyContinue
        Start-Sleep 5
        $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
        $running = $s -and $s.Status -eq 'Running'
    }
    Add-Result "Service $svc" $running "$(if ($s) { $s.Status } else { 'missing' })"
}

# --- Claude gateway: every picker tier must route to its MiniMax model ------
$tierMap = @{
    'claude-sonnet-4-5' = 'MiniMax-M3'
    'claude-opus-4-6'   = 'MiniMax-M2.7'
    'claude-haiku-4-5'  = 'MiniMax-M2.7-highspeed'
}
$headers = @{ 'X-Api-Key' = $token; 'anthropic-version' = '2023-06-01'; 'Content-Type' = 'application/json' }
foreach ($alias in $tierMap.Keys) {
    try {
        $body = '{"model":"' + $alias + '","max_tokens":24,"messages":[{"role":"user","content":"say ok"}]}'
        $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:48217/anthropic/v1/messages' -Method POST -Headers $headers -Body $body -TimeoutSec 90 -UseBasicParsing
        $model = ($resp.Content | ConvertFrom-Json).model
        Add-Result "Claude tier $alias" ($model -eq $tierMap[$alias]) "-> $model (want $($tierMap[$alias]))"
    } catch {
        Add-Result "Claude tier $alias" $false $_.Exception.Message
    }
}

# --- Codex gateway ----------------------------------------------------------
try {
    $body = '{"model":"MiniMax-M3","input":[{"role":"user","content":[{"type":"input_text","text":"say ok"}]}],"max_output_tokens":24,"stream":false}'
    $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:48218/v1/responses' -Method POST -Headers @{ 'Content-Type' = 'application/json'; 'Authorization' = 'Bearer local' } -Body $body -TimeoutSec 90 -UseBasicParsing
    $ok = ($resp.Content | ConvertFrom-Json).output.Count -gt 0
    Add-Result 'Codex gateway :48218' $ok 'POST /v1/responses'
} catch {
    Add-Result 'Codex gateway :48218' $false $_.Exception.Message
}

# --- Codex model catalog ----------------------------------------------------
$catalog = 'C:\Users\Admin\.codex\model-catalogs\minimax-catalog.json'
$catalogOk = $false
if (Test-Path $catalog) {
    try {
        $slugs = ((Get-Content $catalog -Raw | ConvertFrom-Json).models | ForEach-Object slug)
        $catalogOk = @('MiniMax-M3', 'MiniMax-M2.7', 'MiniMax-M2.7-highspeed') | ForEach-Object { $slugs -contains $_ } | Where-Object { -not $_ } | Measure-Object | ForEach-Object { $_.Count -eq 0 }
    } catch { }
}
Add-Result 'Codex model catalog' $catalogOk $catalog

# --- Claude registry --------------------------------------------------------
$reg = Get-ItemProperty -Path 'HKCU:\SOFTWARE\Policies\Claude' -ErrorAction SilentlyContinue
Add-Result 'Claude registry gateway' ($reg.inferenceGatewayBaseUrl -eq 'http://127.0.0.1:48217/anthropic') "$($reg.inferenceGatewayBaseUrl)"

# --- mini MCP orchestrator: targeted server checks ---------------------------
# Avoid mini status here: its all-server concurrent cold probe can time out and
# leave unrelated children behind. Targeted ls is deterministic and exercises
# the same handshake needed by either desktop client.
foreach ($server in @('minimax', 'minimax-media', 'minimax-coding-plan', 'touchpoint', 'winremote', 'daves-tools-harness')) {
    try {
        $listing = & 'C:\Users\Admin\go\bin\mini.exe' ls $server 2>&1 | Out-String
        $ok = ($LASTEXITCODE -eq 0) -and ($listing -match '(?m)^TOOL\s')
        $detail = (($listing -split "`r?`n") | Where-Object { $_ -match '^TOOL\s|^\S+\(' } | Select-Object -First 2) -join ' '
        Add-Result "MCP $server" $ok $detail.Trim()
    } catch {
        Add-Result "MCP $server" $false $_.Exception.Message
    }
}

# --- CoworkVMService must not lock Claude package ----------------------------
$cowork = Get-Service -Name 'CoworkVMService' -ErrorAction SilentlyContinue
$coworkOk = (-not $cowork) -or ($cowork.Status -ne 'Running')
if (-not $coworkOk -and $Fix) {
    Stop-Service -Name 'CoworkVMService' -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
    $cowork = Get-Service -Name 'CoworkVMService' -ErrorAction SilentlyContinue
    $coworkOk = $cowork.Status -ne 'Running'
}
Add-Result 'CoworkVMService not running' $coworkOk "$(if ($cowork) { $cowork.Status } else { 'absent' })"

# --- Report ------------------------------------------------------------------
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$failCount = ($results | Where-Object Status -eq 'FAIL').Count
$results | Format-Table -AutoSize | Out-String | Write-Host
"[$stamp] $(if ($failCount -eq 0) { 'HEALTHY' } else { "$failCount FAILURES" }) :: " +
    (($results | ForEach-Object { "$($_.Check)=$($_.Status)" }) -join '; ') | Add-Content -Path $LogFile

if ($failCount -eq 0) {
    Write-Host 'MiniMax stack: HEALTHY' -ForegroundColor Green
    exit 0
} else {
    Write-Host "MiniMax stack: $failCount check(s) FAILED$(if (-not $Fix) { ' (re-run with -Fix to attempt repair)' })" -ForegroundColor Red
    exit 1
}
