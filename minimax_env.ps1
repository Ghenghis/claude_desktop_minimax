# Load MiniMax keys from the first available private drive (C, G, or S)
$privateDrives = @("C:\\Private", "G:\\Private", "S:\\Private")
$privateRoot = $privateDrives | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $privateRoot) {
    throw "No private drive found. Create C:\\Private, G:\\Private, or S:\\Private and place minimax_key.txt and minimax_api_key.txt there."
}

$tokenFile = Join-Path $privateRoot "minimax_key.txt"
$apiFile = Join-Path $privateRoot "minimax_api_key.txt"

if (-not (Test-Path $tokenFile)) { throw "Missing $tokenFile" }
if (-not (Test-Path $apiFile)) { throw "Missing $apiFile" }

$env:ANTHROPIC_AUTH_TOKEN = (Get-Content $tokenFile -Raw).Trim()
$env:ANTHROPIC_API_KEY = $env:ANTHROPIC_AUTH_TOKEN
$env:ANTHROPIC_BASE_URL = "https://api.minimax.io/anthropic"
$env:MINIMAX_API_KEY = (Get-Content $apiFile -Raw).Trim()
$env:ANTHROPIC_MODEL = "MiniMax-M3"
$env:ANTHROPIC_SMALL_FAST_MODEL = "MiniMax-M3"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "MiniMax-M3"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "MiniMax-M3"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "MiniMax-M3"

Write-Host "MiniMax env loaded from $privateRoot" -ForegroundColor Green
