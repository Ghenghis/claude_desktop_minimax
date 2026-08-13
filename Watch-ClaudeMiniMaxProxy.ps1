# Watchdog: ensure claude-minimax-proxy is always listening on 127.0.0.1:48217.
# Restarts the proxy if it dies. Idempotent -- safe to run repeatedly.
# Use:  powershell -NoProfile -File G:\Github\claude-codex-devin\Watch-ClaudeMiniMaxProxy.ps1
#
# Stop: ctrl-C, or Stop-Process -Name python (kills the child) -- this watchdog then exits.

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $PSCommandPath
$port = 48217
$logDir = 'G:\Github\claude-codex-devin\AICE_DATA'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir 'claude-minimax-proxy.watch.log'

function Test-Listening {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $c
}

function Test-Healthy {
    # Bug #8: a hung-but-listening proxy now passes Test-Listening. Probe
    # /readyz to verify the proxy is actually responsive AND has successfully
    # talked to MiniMax at least once since startup.
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$port/readyz" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Start-Proxy {
    param()
    $env:CLAUDE_MINIMAX_PROXY_PORT = $port
    $env:MINIMAX_ENV_FILE = 'G:\private\.env'
    $py = (Get-Command python.exe -ErrorAction Stop).Source
    Start-Process -FilePath $py -ArgumentList (Join-Path $scriptDir 'claude-minimax-proxy.py') `
        -RedirectStandardOutput (Join-Path $logDir 'claude-minimax-proxy.out') `
        -RedirectStandardError  (Join-Path $logDir 'claude-minimax-proxy.err') `
        -WindowStyle Hidden -PassThru | Out-Null
    Write-Watchlog "started new proxy pid=$pid"
}

function Write-Watchlog {
    param($msg)
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    "$stamp  $msg" | Tee-Object -FilePath $logFile -Append | Write-Host
}

Write-Watchlog "watchdog starting on port $port (ctrl-C to stop)"

# If already running, just report and exit (idempotent).
if (Test-Listening) {
    $owner = (Get-NetTCPConnection -LocalPort $port -State Listen).OwningProcess
    Write-Watchlog "proxy already listening on $port (pid $owner) -- no action needed"
    exit 0
}

Start-Proxy
Start-Sleep -Seconds 2
if (-not (Test-Listening)) {
    Write-Watchlog 'proxy failed to come up after start; aborting'
    exit 1
}

Write-Watchlog 'proxy is up; entering monitor loop (poll every 15s)'
while ($true) {
    Start-Sleep -Seconds 15
    # Bug #8: probe both LISTEN and /readyz (health). A hung-but-listening
    # proxy used to pass; /readyz catches it.
    $listening = Test-Listening
    $healthy = $false
    if ($listening) {
        $healthy = Test-Healthy
    }
    if (-not $listening -or -not $healthy) {
        $reason = if (-not $listening) { 'port closed' } else { '/readyz failed (hung)' }
        Write-Watchlog "proxy is DOWN ($reason) -- restarting"
        Start-Proxy
        Start-Sleep -Seconds 2
        if (Test-Listening -and (Test-Healthy)) {
            Write-Watchlog 'proxy is back UP'
        } else {
            Write-Watchlog 'restart failed'
        }
    }
}
