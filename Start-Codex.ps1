. $PSScriptRoot\\minimax_env.ps1

# Run Codex on the paid OpenAI/Codex plan first
& codex @args
$primaryExit = $LASTEXITCODE

if ($primaryExit -ne 0) {
    Write-Host "Paid Codex plan failed (exit $primaryExit). Switching to MiniMax backup..." -ForegroundColor Yellow
    & codex -c 'model_provider="minimax"' -c 'model="MiniMax-M3"' @args
}
