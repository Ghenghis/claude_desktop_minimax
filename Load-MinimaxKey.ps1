# Explicit, current-process only. Never return or display credentials.
$ErrorActionPreference = 'Stop'
$keyFile = 'C:\private\.env'
$value = $null
foreach ($line in [IO.File]::ReadAllLines($keyFile)) {
    if ($line -match '^\s*(?:export\s+)?MINIMAX_API_KEY\s*=\s*(.+?)\s*$') {
        $value = $Matches[1].Trim().Trim('"').Trim("'")
        break
    }
}
if (-not $value) { throw 'MINIMAX_API_KEY is missing from C:\private\.env.' }
$env:MINIMAX_API_KEY = $value
$value = $null
