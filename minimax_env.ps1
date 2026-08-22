# Load MiniMax keys from the first available private drive (C, G, or S)
$privateDrives = @("C:\\Private")
$privateRoot = $privateDrives | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $privateRoot) {
    throw "No private drive found. Create C:\\Private, G:\\Private, or S:\\Private and place minimax_key.txt, minimax_api_key.txt, or a .env file with MINIMAX_API_KEY."
}

$tokenFile = Join-Path $privateRoot "minimax_key.txt"
$apiFile = Join-Path $privateRoot "minimax_api_key.txt"
$envFile = Join-Path $privateRoot ".env"

function Get-EnvValue([string]$path, [string]$key) {
    if (-not (Test-Path $path)) { return $null }
    $raw = Get-Content -LiteralPath $path -Raw
    $m = [regex]::Match($raw, '(?m)^' + [regex]::Escape($key) + '\s*=\s*(.+?)\s*$')
    if (-not $m.Success) { return $null }
    $v = $m.Groups[1].Value
    if (($v.Length -ge 2) -and ($v[0] -eq $v[-1]) -and ($v[0] -in "'", '"')) {
        $v = $v.Substring(1, $v.Length - 2)
    }
    return $v
}

$anthropicToken = if (Test-Path $tokenFile) { (Get-Content $tokenFile -Raw).Trim() } else { Get-EnvValue $envFile 'MINIMAX_API_KEY' }
$minimaxApiKey = if (Test-Path $apiFile) { (Get-Content $apiFile -Raw).Trim() } else { Get-EnvValue $envFile 'MINIMAX_API_KEY' }

if (-not $anthropicToken) { throw "Missing Anthropic token. Provide $tokenFile or .env with MINIMAX_API_KEY." }
if (-not $minimaxApiKey) { throw "Missing MiniMax API key. Provide $apiFile or .env with MINIMAX_API_KEY." }

$env:ANTHROPIC_AUTH_TOKEN = $anthropicToken
$env:ANTHROPIC_API_KEY = $env:ANTHROPIC_AUTH_TOKEN
$env:ANTHROPIC_BASE_URL = "https://api.minimax.io/anthropic"
$env:MINIMAX_API_KEY = $minimaxApiKey
$env:ANTHROPIC_MODEL = "MiniMax-M3"
$env:ANTHROPIC_SMALL_FAST_MODEL = "MiniMax-M3"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "MiniMax-M3"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "MiniMax-M3"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "MiniMax-M3"

Write-Host "MiniMax env loaded from $privateRoot" -ForegroundColor Green
