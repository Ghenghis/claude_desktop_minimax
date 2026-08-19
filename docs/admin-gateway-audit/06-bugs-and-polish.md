# Admin Gateway — Bug Audit & Polish List (Aug 2026)

**Scope:** Every file in `G:\Github\claude-codex-devin` that ships with the Admin Gateway (Python proxy + 11 PowerShell scripts). Issues are grouped by severity. The 31 items below extend the existing "Known limitations" section in `01-current-features.md` with concrete file:line citations and one-line fixes.

## Critical (must fix before next user-facing change)

### 1. Proxy `HTTPError` handler corrupts response on partial failure
**File:** `claude-minimax-proxy.py:241-249`
**Problem:** `send_response(e.code)` is called before `e.read()`. If the error-body read raises, the outer `except Exception` at line 250 calls `_send_json(502, ...)` which calls `send_response` a second time on an already-started response. Client sees a broken HTTP frame.
**Fix:** wrap `e.read()` in its own try/except and close the connection on failure instead of sending a fresh response.

### 2. Broad `except Exception` swallows `KeyboardInterrupt` / `SystemExit`
**File:** `claude-minimax-proxy.py:250`
**Problem:** Catches all exceptions including shutdown signals, blocking clean Ctrl+C handling in the proxy thread.
**Fix:** narrow to `(URLError, socket.timeout, OSError, ConnectionError, json.JSONDecodeError)`.

### 3. Watchdog logs the wrong PID
**File:** `Watch-ClaudeMiniMaxProxy.ps1:24-28`
**Problem:** `Start-Process ... -PassThru | Out-Null` discards the launched process object, so `$pid` in the log line refers to the PowerShell host PID, not the Python child.
**Fix:** `$proc = Start-Process ... -PassThru; Write-Watchlog "started pid=$($proc.Id)"`.

### 4. Watchdog has no Ctrl+C cleanup
**File:** `Watch-ClaudeMiniMaxProxy.ps1:54-62`
**Problem:** `while ($true)` with no `trap` / `try/finally`; Ctrl+C in the watchdog window leaves the hidden Python child running and port 48217 still bound.
**Fix:** wrap the loop in `try { ... } finally { Get-NetTCPConnection ... | Stop-Process -Force }`.

### 5. `Harden-MinimaxEnv.ps1` grants ACL to wrong user under elevation
**File:** `Harden-MinimaxEnv.ps1:31,45`
**Problem:** `$meAcct = $env:USERNAME` reflects the unelevated caller, but the elevated token is Administrator. The new allow-rule permits the original user but not the elevated admin that runs `Set-Acl`, so subsequent admin reads of the file 401/deny.
**Fix:** derive `$meAcct` from `[Security.Principal.WindowsIdentity]::GetCurrent().User.Translate([Security.Principal.NTAccount]).Value`.

## High (should fix soon)

### 6. No `Content-Length` validation or body cap
**File:** `claude-minimax-proxy.py:179-180`
**Problem:** `int(self.headers.get("Content-Length", 0))` raises `ValueError` on garbage input and hangs/crashes on oversized values; no max-body guard.
**Fix:** wrap in try/except returning 400; cap reads at 50 MB.

### 7. Unknown model silently routes to flagship
**File:** `claude-minimax-proxy.py:104-106,189-190`
**Problem:** `pick_minimax_model("garbage")` returns `MiniMax-M3`, burning flagship quota on typos.
**Fix:** return 400 `{"error":"unsupported model"}` when name not in `MODEL_MAP`.

### 8. Watchdog checks TCP listen only, not process identity
**File:** `Watch-ClaudeMiniMaxProxy.ps1:14-17,54-61`
**Problem:** Any process bound to 48217 satisfies the check; a hung Python proxy that still holds the socket is never restarted.
**Fix:** also `Invoke-WebRequest http://127.0.0.1:$port/v1/models` periodically.

### 9. `Load-MinimaxKey.ps1` regex does not strip `#` comments
**File:** `Load-MinimaxKey.ps1:19`
**Problem:** `^MINIMAX_API_KEY\s*=\s*(.+?)\s*$` captures trailing `# whatever` into the value if the line is unquoted.
**Fix:** `(?m)^MINIMAX_API_KEY\s*=\s*("[^"]*"|'[^']*'|[^#\r\n]*)`.

### 10. `Stop-ClaudeMiniMaxProxy.ps1` kills any process on 48217
**File:** `Stop-ClaudeMiniMaxProxy.ps1:3-5`
**Problem:** No ownership/PID check; if a non-Python process happens to bind the port it is force-stopped.
**Fix:** filter `Get-NetTCPConnection` results to `ProcessName -eq 'python'` before `Stop-Process`.

### 11. `Test-ClaudeMiniMaxSetup.ps1` uses the wrong key
**File:** `Test-ClaudeMiniMaxSetup.ps1:54`
**Problem:** Sends `X-Api-Key = $env:ANTHROPIC_AUTH_TOKEN` (loaded from `minimax_key.txt` by `minimax_env.ps1:15`), but the proxy injects `MINIMAX_API_KEY` from `G:\private\.env`. If the two files hold different values the test passes against a key the proxy never uses.
**Fix:** have `minimax_env.ps1` set `$env:MINIMAX_API_KEY` from the same `minimax_api_key.txt`, or call `Load-MinimaxKey.ps1` in the test.

### 12. `minimax_env.ps1` collapses all model tiers to M3
**File:** `minimax_env.ps1:19-23`
**Problem:** Sets `_SONNET/_OPUS/_HAIKU_MODEL` all to `MiniMax-M3`, ignoring the tier routing the proxy implements (M3/M2.7/M2.1). Diverges silently from `MODEL_MAP`.
**Fix:** set each tier to its corresponding MiniMax model.

### 13. `Harden-MinimaxEnv.ps1` does not check `takeown.exe` exit code
**File:** `Harden-MinimaxEnv.ps1:21`
**Problem:** `& takeown.exe "/F" "$envPath"` silently continues on failure; `Set-Acl` then errors with a confusing message.
**Fix:** check `$LASTEXITCODE` and throw.

## Medium (polish)

### 14. Inconsistent registry path separator
**File:** `Set-ClaudeDesktopGateway.ps1:5`
**Problem:** Uses `"HKCU:\\SOFTWARE\\..."` (double-backslash). Inconsistent with `Set-ClaudeDesktopInference.ps1:11` which uses `HKCU:\`.
**Fix:** normalize to single backslash.

### 15. Per-request `.env` re-read on disk
**File:** `claude-minimax-proxy.py:209`
**Problem:** Each POST opens/parses the file. Cheap but pointless; rotating the key requires a proxy restart.
**Fix:** load once at startup; watch the file's mtime for hot-reload.

### 16. Empty-quote key yields empty key
**File:** `claude-minimax-proxy.py:62-64`
**Problem:** `MINIMAX_API_KEY=""` parses to empty string; returns empty from `load_minimax_key`; upstream returns 401 with no clear local signal.
**Fix:** skip empty values in `_parse_dotenv`.

### 17. Streaming response has no client-disconnect handling
**File:** `claude-minimax-proxy.py:233-240`
**Problem:** `wfile.write` on a closed socket raises mid-loop; only the broad `except Exception` catches it but the chunked trailer (`0\r\n\r\n`) may not be written.
**Fix:** catch `BrokenPipeError` per-chunk and stop the loop silently.

### 18. `Test-MinimaxEnvACL.ps1` regex is loose
**File:** `Test-MinimaxEnvACL.ps1:37-41`
**Problem:** `-match 'Read|Modify|FullControl|Write'` misses `GenericRead`, `ReadData`, etc.
**Fix:** use `[Enum]::GetValues([Security.AccessControl.FileSystemRights])` or strict ACE flag checks.

### 19. `/v1/messages/count_tokens` stub returns 0
**File:** `claude-minimax-proxy.py:170-174`
**Problem:** Real token count is needed by some clients.
**Fix:** at minimum, count input tokens locally via `len(json.dumps(body["messages"])) // 4` heuristic; better, parse upstream response.

### 20. `Watch-ClaudeMiniMaxProxy.ps1:24` does not set `WorkingDirectory`
**File:** `Watch-ClaudeMiniMaxProxy.ps1:24`
**Problem:** `Start-Process` defaults to `$env:SystemRoot`; any future relative path in the proxy fails.
**Fix:** `-WorkingDirectory $scriptDir`.

### 21. `Set-ClaudeDesktopInference.ps1` is functionally subsumed by `Set-ClaudeDesktopGateway.ps1`
**File:** `Set-ClaudeDesktopInference.ps1`
**Problem:** Both write the same registry keys; the former is dead code.
**Fix:** delete `Set-ClaudeDesktopInference.ps1` or have it call the newer script.

### 22. `Harden-MinimaxEnv.ps1:45` uses `Win32_UserAccount` (local accounts only)
**File:** `Harden-MinimaxEnv.ps1:45`
**Problem:** Domain users return null; owner is not set.
**Fix:** use `[Security.Principal.WindowsIdentity]::GetCurrent().User` and `Translate` to NTAccount.

### 23. `Watch-ClaudeMiniMaxProxy.ps1` doesn't fail helpfully when `python.exe` missing
**File:** `Watch-ClaudeMiniMaxProxy.ps1:23`
**Problem:** `Get-Command ... -ErrorAction Stop` throws, but message is opaque.
**Fix:** validate and print a one-liner pointing to `python -m venv` guidance.

## Low (nice to have)

### 24. `OPTIONS` handler is path-agnostic
**File:** `claude-minimax-proxy.py:121-126`
**Problem:** Returns 204 for any path; should restrict to known endpoints.

### 25. Dead `or path` fallback
**File:** `claude-minimax-proxy.py:165`
**Problem:** `path[len("/anthropic"):]` is empty for `/anthropic`, so `or path` returns `/anthropic` itself, which falls through to 404. Cosmetic.

### 26. Mixed-case paths in `.env` candidate list
**File:** `claude-minimax-proxy.py:36-40`
**Problem:** `G:\private\.env` and `G:\Private\.env` duplicates; dedupe.

### 27. `Start-ClaudeMiniMaxProxy.ps1:14` no PATH check
**File:** `Start-ClaudeMiniMaxProxy.ps1:14`
**Problem:** `python $proxy` with no PATH check; surface `where.exe python` error.

### 28. `Test-ClaudeMiniMaxSetup.ps1:65` overwrites built-in `$matches`
**File:** `Test-ClaudeMiniMaxSetup.ps1:65`
**Problem:** PowerShell built-in `$matches` is reused; rename to a local variable.

### 29. `minimax_env.ps1:2` double-backslash in literals
**File:** `minimax_env.ps1:2`
**Problem:** Double-backslashes in path literals; normalize.

### 30. `claude-minimax-proxy.py:111` uses `print(..., file=sys.stderr)` for logs
**File:** `claude-minimax-proxy.py:111`
**Problem:** No rotation, no JSON structure, no redaction.
**Fix:** switch to `logging` with rotation.

### 31. `claude-minimax-proxy.py:104-106` should log when model name is unmapped
**File:** `claude-minimax-proxy.py:104-106`
**Problem:** Silent fallback hides client misconfiguration.
**Fix:** `print(f"[model-map] unknown '{name}', defaulting to M3", file=sys.stderr)`.

## Per-file summary

| File | Critical | High | Medium | Low | Total |
|---|---|---|---|---|---|
| `claude-minimax-proxy.py` | 2 | 3 | 3 | 3 | 11 |
| `Watch-ClaudeMiniMaxProxy.ps1` | 2 | 1 | 1 | 1 | 5 |
| `Harden-MinimaxEnv.ps1` | 1 | 1 | 2 | 0 | 4 |
| `Set-ClaudeDesktopGateway.ps1` | 0 | 0 | 2 | 0 | 2 |
| `Load-MinimaxKey.ps1` | 0 | 1 | 0 | 0 | 1 |
| `Stop-ClaudeMiniMaxProxy.ps1` | 0 | 1 | 0 | 0 | 1 |
| `minimax_env.ps1` | 0 | 1 | 0 | 1 | 2 |
| `Test-ClaudeMiniMaxSetup.ps1` | 0 | 1 | 0 | 1 | 2 |
| `Test-MinimaxEnvACL.ps1` | 0 | 0 | 1 | 0 | 1 |
| `Start-ClaudeMiniMaxProxy.ps1` | 0 | 0 | 0 | 1 | 1 |
| `Set-ClaudeDesktopInference.ps1` | 0 | 0 | 0 | 0 | 0 (subsumed) |
| **Total** | **5** | **9** | **9** | **7** | **30** |

## Suggested order of operations

1. **Critical #1** (proxy HTTPError handler) — 30 min. Pure bug; possible data corruption on partial-failure paths.
2. **Critical #2** (broad except) — 10 min. One-line fix; unblocks clean Ctrl+C.
3. **Critical #3 + #4** (watchdog PID + Ctrl+C) — 20 min. Together.
4. **Critical #5** (Harden user mapping) — 15 min. One-line fix.
5. **High #9** (regex comment stripping) — 5 min. One regex; security-adjacent.
6. **High #11** (test key mismatch) — 30 min. Real risk that test is green against the wrong key.
7. **High #7** (unknown model fallback) — 10 min. Quota-saver.
8. **High #12** (tier collapse) — 10 min. Drift between proxy and `minimax_env.ps1`.
9. **High #6** (Content-Length cap) — 20 min. DoS hardening.
10. Remaining high and medium items in batches.

Total ≈ 1-2 weekends of polish. No code in this audit should be considered "done" until issues 1–7 are resolved.

## Out-of-scope bugs observed

- **Claude Desktop "Bypass permissions" mode UI bug**: shows "Permission mode couldn't be changed. You can try again." on attempt to switch. This is upstream in Claude Desktop itself, not in the Admin Gateway — nothing in this codebase can fix it.