# Load the MiniMax API key from S:\private or G:\private into the CURRENT process only.
#
# Usage (from the proxy starter, never interactively):
#   . G:\Github\claude-codex-devin\Load-MinimaxKey.ps1
#
# Guarantees:
#   - Sets $env:MINIMAX_API_KEY in this process only (not exported to User/System)
#   - Never echoes, prints, or returns the key value
#   - Adds no entry to the host PowerShell history beyond the dot-source path

$ErrorActionPreference = 'Stop'

$value = $null

# Prefer S:\private (fastest), then G:\private.
$privateRoots = @('S:\private', 'G:\private')

foreach ($root in $privateRoots) {
    $keyFile = Join-Path $root 'minimax_key.txt'
    $envFile = Join-Path $root '.env'
    if (Test-Path -LiteralPath $keyFile) {
        $value = (Get-Content -LiteralPath $keyFile -Raw).Trim()
        if ($value) { break }
    }
    if (Test-Path -LiteralPath $envFile) {
        $raw = Get-Content -LiteralPath $envFile -Raw
        $found = [regex]::Matches($raw, '(?m)^MINIMAX_API_KEY\s*=\s*(.+?)\s*$')
        if ($found.Count -gt 0) {
            $value = $found[0].Groups[1].Value
            if (($value.Length -ge 2) -and ($value[0] -eq $value[-1]) -and ($value[0] -in "'",'"')) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            if ($value) { break }
        }
    }
}

if (-not $value) {
    throw "MiniMax key not found in S:\private or G:\private (tried minimax_key.txt and .env)"
}

# Per-process only. Do NOT use [Environment]::SetEnvironmentVariable -- that
# would persist to User or Machine and survive logoff.
$env:MINIMAX_API_KEY = $value
