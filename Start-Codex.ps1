# Native paid-plan invocation only. Never replay a failed coding task on another provider.
& codex @args
exit $LASTEXITCODE
