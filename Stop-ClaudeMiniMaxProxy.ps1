# Stop the local Claude <-> MiniMax proxy if it's running
$port = 48217
Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped process $($_.OwningProcess) listening on port $port" -ForegroundColor Green
}
