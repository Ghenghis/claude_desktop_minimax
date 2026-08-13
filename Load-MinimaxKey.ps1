# Load the MiniMax API key from G:\private\.env into the CURRENT process only.
#
# Usage (from the proxy starter, never interactively):
#   . G:\Github\claude-codex-devin\Load-MinimaxKey.ps1
#
# Guarantees:
#   - Sets $env:MINIMAX_API_KEY in this process only (not exported to User/System)
#   - Never echoes, prints, or returns the key value
#   - Adds no entry to the host PowerShell history beyond the dot-source path

$ErrorActionPreference = 'Stop'
$envPath = 'G:\private\.env'

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "MiniMax .env not found at $envPath"
}

$raw = Get-Content -LiteralPath $envPath -Raw
$matches = [regex]::Matches($raw, '(?m)^MINIMAX_API_KEY\s*=\s*(.+?)\s*$')
if ($matches.Count -eq 0) {
    throw "MINIMAX_API_KEY not present in $envPath"
}

$value = $matches[0].Groups[1].Value
if (($value.Length -ge 2) -and ($value[0] -eq $value[-1]) -and ($value[0] -in "'",'"')) {
    $value = $value.Substring(1, $value.Length - 2)
}

# Per-process only. Do NOT use [Environment]::SetEnvironmentVariable -- that
# would persist to User or Machine and survive logoff.
$env:MINIMAX_API_KEY = $value
