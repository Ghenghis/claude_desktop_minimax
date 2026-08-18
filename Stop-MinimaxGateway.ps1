# Stop the claude-minimax-v2 gateway so the next start can use port 48217.
# This script is safe to run even if the gateway is not running.

[CmdletBinding()]
param(
    [int]$Port = 48217,
    [int]$TimeoutSeconds = 5
)

$ErrorActionPreference = 'SilentlyContinue'

function Test-PortFree($targetHost, $targetPort) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect($targetHost, $targetPort)
        $c.Close()
        return $false
    } catch {
        return $true
    }
}

# 1) Kill by command line (the way the gateway is usually started).
$p1 = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*gateway.server*' }
if ($p1) {
    $p1 | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Milliseconds 500
}

# 2) Kill by the TCP port, in case the process has a different command line.
$conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($conn) {
    $conn | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
    Start-Sleep -Milliseconds 500
}

# 3) Wait for the port to become free.
$waited = 0
while ($waited -lt $TimeoutSeconds) {
    if (Test-PortFree '127.0.0.1' $Port) { return $true }
    Start-Sleep -Milliseconds 500
    $waited += 0.5
}

# Still in use.  Tell the user how to finish manually.
Write-Host "Port $Port is still in use." -ForegroundColor Red
Write-Host "Open Task Manager (Ctrl+Shift+Esc), find the 'Python' process that is using port $Port, and click End task." -ForegroundColor Yellow
Write-Host "Then run Start-ClaudeMinimaxV2.ps1 again." -ForegroundColor Yellow
return $false
