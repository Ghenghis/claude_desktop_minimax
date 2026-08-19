---
name: watchdog-self-test
description: |
  Kill the running proxy process and assert the watchdog restarts it within
  a configurable timeout. Use to verify the watchdog is actually working
  after any change to Watch-ClaudeMiniMaxProxy.ps1.
when_to_use: |
  Trigger: after any change to Watch-ClaudeMiniMaxProxy.ps1, after Windows
  Update, after the user reports "Claude Desktop randomly disconnected".
  Don't trigger: in CI (this kills the running proxy and is destructive).
inputs:
  - name: timeout_seconds
    type: integer
    required: false
    default: 60
    description: How long to wait for the watchdog to bring the proxy back.
  - name: dry_run
    type: boolean
    required: false
    default: false
outputs:
  - Exit code 0 if watchdog restarts within timeout, non-zero otherwise.
  - Chat log with timestamps for kill, restart, /readyz pass.
---

# Procedure

1. Verify proxy is currently running: `Get-NetTCPConnection -LocalPort 48217 -State Listen`.
2. Record current PID: `Get-NetTCPConnection -LocalPort 48217 -State Listen | Select -ExpandProperty OwningProcess`.
3. `Stop-Process -Id <pid> -Force`.
4. Loop every 2 seconds up to `timeout_seconds`:
   - `Get-NetTCPConnection -LocalPort 48217 -State Listen | Select -ExpandProperty OwningProcess`
   - new PID? Try `Invoke-WebRequest http://127.0.0.1:48217/readyz -TimeoutSec 5`.
   - 200? Done.
5. If /readyz returns 200 within timeout: success. Print chat log with timestamps.
6. If timeout: print chat log, suggest running `Watch-ClaudeMiniMaxProxy.ps1` manually.

# Examples

```
/watchdog-self-test
/watchdog-self-test --timeout_seconds=120
/watchdog-self-test --dry-run  # just check proxy is alive, don't kill it
```

# Limitations

- Destructive: kills the running proxy. Do not run in CI.
- Assumes the watchdog is registered (via `docs/Claude-Desktop-MiniMax.md:177-179`).
- Does NOT test `/readyz` semantics (i.e., whether the proxy itself is functional).
  It only tests "watchdog restarts the proxy after a kill."