# Load keys and start Codex Desktop on the MiniMax backup profile
. $PSScriptRoot\\minimax_env.ps1

$codexBin = Get-ChildItem -Path "$env:LOCALAPPDATA\OpenAI\Codex\bin" -Recurse -Filter 'codex.exe' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $codexBin) {
    throw "codex.exe not found in $env:LOCALAPPDATA\OpenAI\Codex\bin"
}

& $codexBin.FullName app
