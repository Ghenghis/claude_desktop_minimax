> HISTORICAL DOCUMENT — superseded by README.md and docs/SAFETY_REVIEW.md.
> Do not run old watchdog, permission-bypass, process-kill or repair instructions.

# Architecture

## Request flow

```
Claude Desktop
   |
   |  http://127.0.0.1:48217/anthropic/v1/messages
   |  (model: "claude-sonnet-4-5", X-Proxy-Token: <hash>, content: ...)
   v
+-----------------------------------------+
| claude-minimax-proxy.py                 |
| 127.0.0.1:48217 (loopback only)         |
|                                         |
|  1. Validate X-Proxy-Token (Gap 1)     |
|     -> 401 if missing/wrong              |
|  2. Read body (capped at 50 MB)         |
|  3. Parse JSON, validate picker model   |
|     -> 400 if model not in MODEL_MAP    |
|  4. Compute SHA-256 cache key           |
|     -> return cached if hit (P0 #2)     |
|  5. Walk Model Chains waterfall          |
|     For each target in chain:            |
|       Retry 3x with backoff + Retry-After|
|       On 2xx: cache + return             |
|       On non-2xx: try next link          |
|  6. On all-chain failure: return last   |
|     upstream error                       |
+-----------------------------------------+
   |
   |  https://api.minimax.io/anthropic/v1/messages
   |  (model: "MiniMax-M3" / M2.7 / M2.7-highspeed, X-Api-Key: <real key>)
   v
MiniMax API -> response -> back through proxy -> streamed to client
```

## Trust boundary

The client is **untrusted for credentials**: it never supplies the real key
and its `Authorization`/`X-Api-Key` headers are always discarded. The key
exists only in:

1. The proxy process memory (loaded at startup, refreshed on `.env` mtime change).
2. `G:\private\.env` (ACL-restricted by `Harden-MinimaxEnv.ps1`).
3. Nowhere else — not in the registry, not in logs, not in the environment
   outside the proxy process.

## Key decisions

- **Bind loopback-only** (`127.0.0.1:48217`) — not reachable off-host.
- **Stdlib-only** — Python stdlib, no `pip install` required.
- **Always inject the .env key** — never trust client-supplied auth.
- **Always strip client auth** — placeholder values from Claude Desktop are
  discarded; the real key is read from disk and injected.
- **Always rewrite the model** — Anthropic-looking picker slots map to
  MiniMax models via `MODEL_MAP`; unknown names return 400.
- **Cache deterministic responses** — SHA-256 over canonicalized
  `{model, messages, system, temperature}`; 24h TTL; 512-entry LRU.
- **Failover via Model Chains** — on 5xx after retry exhaustion, try the
  next model in the chain (CCPG-style waterfall).

See `docs/adr/` for the rationale behind each.

## Modules

| File | Purpose |
|---|---|
| `claude-minimax-proxy.py` | The HTTP server (Python stdlib) |
| `Start-ClaudeMiniMaxProxy.ps1` | Foreground launcher |
| `Watch-ClaudeMiniMaxProxy.ps1` | Watchdog (15s `/readyz` probe + auto-restart) |
| `Stop-ClaudeMiniMaxProxy.ps1` | Stop the running proxy |
| `Set-ClaudeDesktopGateway.ps1` | Wire Claude Desktop registry + managed MCP servers |
| `Set-ClaudeDesktopInference.ps1` | Registry-only variant (subsumed by Gateway variant) |
| `Test-ClaudeMiniMaxSetup.ps1` | Live end-to-end smoke (requires a real MiniMax key) |
| `Test-MinimaxEnvACL.ps1` | ACL verification for `G:\private\.env` |
| `Harden-MinimaxEnv.ps1` | One-time ACL tightening |
| `Load-MinimaxKey.ps1` | Process-scoped key loader (never persists env) |
| `minimax_env.ps1` | Alt key loader for `minimax_key.txt` (different file, different scope) |
| `Fix-ClaudePermissions.ps1` | Workaround for Claude Desktop #61304 broken toggle |
| `scripts/Generate-ProxyToken.ps1` | Generate the shared-secret token |
| `scripts/hermes-call.ps1` | Helper for Skills to record HermesProof evidence |

## Harness (Skills + Contracts + HermesProof)

See `.harness/HARNESS.md` for the contract.

## Observability

- `GET /healthz` — always 200 if the proxy is alive.
- `GET /readyz` — 200 if (a) `.env` key loaded AND (b) we've successfully talked
  to MiniMax at least once since startup.
- Per-request stderr log: `[key-path]`, `[chain]`, `[proxy error]` lines.
- HermesProof evidence ledger entries (hash-chained) for every Skill run.