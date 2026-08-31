> HISTORICAL DOCUMENT — superseded by README.md and docs/SAFETY_REVIEW.md.
> Do not run old watchdog, permission-bypass, process-kill or repair instructions.

# Admin Gateway — Current Features

**Scope:** the local third-party inference gateway in `G:\Github\claude-codex-devin` that lets Claude Desktop talk to MiniMax via the Anthropic-compatible API. The implementation is intentionally minimal: one ~270-line stdlib-only Python proxy and a small set of PowerShell scripts that wire registry keys, load a secret from a local `.env`, and run a watchdog.

## 1. Overview

The **Admin Gateway** is a Windows-local, single-user inference gateway. It exists to work around a Claude Desktop client-side validator that rejects non-Anthropic model IDs in `inferenceModels` (`docs/Claude-Desktop-MiniMax.md:13-23`). The implementation rewrites Anthropic-looking names to `MiniMax-M3` / M2.7 / M2.1 and forwards to `https://api.minimax.io/anthropic/v1/messages`.

**Users:** the repo owner on a single Windows machine (`claude-desktop.md:180` confirms no multi-tenant story).
**Deployment model:** single-process loopback HTTP proxy on `127.0.0.1:48217`, bound only to loopback, started by the user from a kept-open PowerShell window (`Start-ClaudeMiniMaxProxy.ps1:5-14`) or auto-restarted by a watchdog (`Watch-ClaudeMiniMaxProxy.ps1:54-61`).

## 2. Current features

| Feature | Implemented in | Evidence |
|---|---|---|
| Local loopback HTTP listener (stdlib only, no deps) | `claude-minimax-proxy.py` | `:25-29,255` |
| `GET /v1/models` discovery with `anthropic_family_tier` shim | `claude-minimax-proxy.py` | `:128-159` |
| `POST /v1/messages` model-name rewrite (Anthropic → MiniMax) | `claude-minimax-proxy.py` | `:161-176,178-191` |
| `/anthropic` URL prefix normalization | `claude-minimax-proxy.py` | `:163-165` |
| `POST /v1/messages/count_tokens` stub returning `input_tokens:0` | `claude-minimax-proxy.py` | `:170-174` |
| 3-tier picker routing (sonnet→M3, opus→M2.7, haiku→M2.1) | `claude-minimax-proxy.py` | `:93-102` |
| Forced credential override — discards client `Authorization`/`X-Api-Key`, injects `.env` key | `claude-minimax-proxy.py` | `:196-214` |
| SSE chunked streaming pass-through | `claude-minimax-proxy.py` | `:229-240` |
| CORS preflight (`OPTIONS`) | `claude-minimax-proxy.py` | `:121-126` |
| `.env` loader (KEY=VALUE, quotes, `#`, `export`) | `claude-minimax-proxy.py` | `:44-65,68-85` |
| Process-scoped key load (no User/Machine env var) | `Load-MinimaxKey.ps1` | `:11,29-31` |
| Claude Desktop registry wiring (Gateway mode, model list) | `Set-ClaudeDesktopInference.ps1`, `Set-ClaudeDesktopGateway.ps1` | `Set-ClaudeDesktopInference.ps1:11-20`; `Set-ClaudeDesktopGateway.ps1:5-23` |
| Managed MCP servers (hermes3d-locks, hp-mha-serena, minimax-media) | `Set-ClaudeDesktopGateway.ps1` | `:44-81` |
| Local-dev MCP toggle + `unstableDisableModelVerification` cleanup | `Set-ClaudeDesktopGateway.ps1` | `:24,81` |
| Loopback-port watchdog + log file | `Watch-ClaudeMiniMaxProxy.ps1` | `:14-17,19-29,54-61` |
| Idempotent "already listening" exit | `Watch-ClaudeMiniMaxProxy.ps1` | `:40-44` |
| Key ACL hardening (inheritance off, deny Everyone, owner=current user) | `Harden-MinimaxEnv.ps1` | `:26-42,44-51` |
| ACL verifier (lengths only, never the value) | `Test-MinimaxEnvACL.ps1` | `:37-55` |
| Drive-fallback key loader for Claude-Code-style env (C/G/S) | `minimax_env.ps1` | `:2-23` |
| One-shot proxy launcher | `Start-ClaudeMiniMaxProxy.ps1` | `:5-14` |

## 3. Architecture

```
   +----------------------+   HTTP/1.1, loopback only
   |   Claude Desktop     |   Headers: Authorization / X-Api-Key (always placeholder,
   |   (Windows client)   |   ignored by proxy), Content-Type, anthropic-version
   +----------+-----------+
              |  POST /anthropic/v1/messages     (claude-sonnet-4-5 | -opus-4-6 | -haiku-4-5)
              v
+---------------------------------------------------------------+
|  claude-minimax-proxy.py                                     |
|  127.0.0.1:48217  (ThreadingHTTPServer)                       |
|                                                               |
|   do_GET  /v1/models, /anthropic/v1/models   -> 200 shim      |
|   do_POST /anthropic/v1/messages -> /v1/messages              |
|                                                               |
|   1) Strip  Authorization, X-Api-Key from client             |
|   2) Rewrite payload "model"  via MODEL_MAP                   |
|       sonnet -> MiniMax-M3     opus -> MiniMax-M2.7           |
|       haiku  -> MiniMax-M2.1                                  |
|   3) Inject X-Api-Key = MINIMAX_API_KEY from G:\private\.env  |
|   4) Forward to TARGET_BASE + "/v1/messages"                  |
|                                                               |
|   Errors -> 400/404/502; SSE streams chunked; HTTPError       |
|   body proxied verbatim                                       |
+----------------------------+----------------------------------+
                             |  HTTPS
                             v
                https://api.minimax.io/anthropic/v1/messages
                             |
                             v
                       MiniMax backend
                       (M3 / M2.7 / M2.1)

Side channel (registry): HKCU\SOFTWARE\Policies\Claude
  inferenceProvider          = "gateway"
  inferenceGatewayBaseUrl    = "http://127.0.0.1:48217/anthropic"
  inferenceGatewayApiKey     = "proxy-managed"   (placeholder)
  inferenceGatewayAuthScheme = "x-api-key"
  modelDiscoveryEnabled      = "true"
  inferenceModels            = [sonnet / opus / haiku entries]
  managedMcpServers          = [hermes3d-locks, hp-mha-serena, minimax-media]
  isLocalDevMcpEnabled       = "true"
```

## 4. Configuration surface

| Knob | Type | Default | Where |
|---|---|---|---|
| `CLAUDE_MINIMAX_PROXY_PORT` | env int | `48217` | `claude-minimax-proxy.py:29`; set by `Start-ClaudeMiniMaxProxy.ps1:8` and `Watch-ClaudeMiniMaxProxy.ps1:21` |
| `MINIMAX_ENV_FILE` | env path | none (uses hard-coded candidate list) | `claude-minimax-proxy.py:34-41`; set by `Start-ClaudeMiniMaxProxy.ps1:9` and `Watch-ClaudeMiniMaxProxy.ps1:22` |
| `MINIMAX_API_KEY` / `MINIMAX_KEY` | dotenv key | required | `claude-minimax-proxy.py:82`; consumed via `Load-MinimaxKey.ps1:19-31` |
| `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` / `…_SMALL_FAST_MODEL` / `…_SONNET/OPUS/HAIKU_MODEL` | env (Claude-Code-style path) | `https://api.minimax.io/anthropic`, `MiniMax-M3` | `minimax_env.ps1:15-23` |
| Port literal | hard-coded | `48217` | `Start-ClaudeMiniMaxProxy.ps1:5`, `Watch-ClaudeMiniMaxProxy.ps1:9` |
| Log directory | hard-coded | `G:\Github\claude-codex-devin\AICE_DATA` | `Watch-ClaudeMiniMaxProxy.ps1:10-12` |
| Registry path | hard-coded | `HKCU:\SOFTWARE\Policies\Claude` | `Set-ClaudeDesktopInference.ps1:11`; `Set-ClaudeDesktopGateway.ps1:5` |
| `inferenceGatewayBaseUrl` | registry string | `http://127.0.0.1:48217/anthropic` | `Set-ClaudeDesktopInference.ps1:15`; `Set-ClaudeDesktopGateway.ps1:12` |
| `inferenceGatewayApiKey` | registry string | `"proxy-managed"` (placeholder) | `Set-ClaudeDesktopInference.ps1:17`; `Set-ClaudeDesktopGateway.ps1:16` |
| `inferenceGatewayAuthScheme` | registry string | `"x-api-key"` | `Set-ClaudeDesktopInference.ps1:18`; `Set-ClaudeDesktopGateway.ps1:17` |
| `inferenceModels` | registry JSON string | sonnet / opus / haiku trio | `Set-ClaudeDesktopInference.ps1:20`; `Set-ClaudeDesktopGateway.ps1:23` |
| `modelDiscoveryEnabled` | registry string | `"true"` | `Set-ClaudeDesktopInference.ps1:19`; `Set-ClaudeDesktopGateway.ps1:18` |
| `unstableDisableModelVerification` | registry (removed) | — | `Set-ClaudeDesktopGateway.ps1:24` |
| `managedMcpServers` | registry JSON string | 3 servers | `Set-ClaudeDesktopGateway.ps1:44-80` |
| `isLocalDevMCPEnabled` | registry string | `"true"` | `Set-ClaudeDesktopGateway.ps1:81` |
| `MCP_LOCK_WORKSPACE`, `HERMES_WORKSPACE_ROOT` | MCP env | `$PSScriptRoot` | `Set-ClaudeDesktopGateway.ps1:50,58-61` |

There are no CLI flags to the proxy — `python claude-minimax-proxy.py` is invoked as-is (`Start-ClaudeMiniMaxProxy.ps1:14`, `Watch-ClaudeMiniMaxProxy.ps1:24-27`).

## 5. Security posture

**Secret storage.** The MiniMax key lives in plaintext in `G:\private\.env` (`Load-MinimaxKey.ps1:12`, `claude-minimax-proxy.py:34-41`). The proxy's `.env` candidate list also hard-codes `G:\private\.env`, `C:\private\.env`, `S:\private\.env` and case variants (`claude-minimax-proxy.py:36-40`). `Harden-MinimaxEnv.ps1:26-42` disables inheritance, strips existing ACEs, grants `Read` to the current user and `SYSTEM`, and adds an explicit `Deny Everyone FullControl`. The verifier (`Test-MinimaxEnvACL.ps1:37-48`) treats any non-owner/non-`SYSTEM`/non-`BUILTIN\Administrators` ACE carrying Read/Modify/FullControl/Write as a failure.

**Secret loading.** `Load-MinimaxKey.ps1:29-31` deliberately uses `$env:MINIMAX_API_KEY = …` (process-scope) and explicitly comments that `[Environment]::SetEnvironmentVariable` "would persist to User or Machine and survive logoff". The proxy re-reads `.env` per request (`claude-minimax-proxy.py:209`), holding the value in process memory.

**Secret rotation.** Only documented path is "revoke in MiniMax console, edit `G:\private\.env`, restart the proxy window" (`docs/Claude-Desktop-MiniMax.md:201-208`). No key-versioning, expiry, or multi-key support exists.

**Credential scope.** The registry stores the literal string `proxy-managed` (`Set-ClaudeDesktopInference.ps1:17`, `Set-ClaudeDesktopGateway.ps1:16`). The proxy **always** strips client-supplied `Authorization`/`X-Api-Key` and injects the real key from `.env` (`claude-minimax-proxy.py:196-214`), logging only the byte length to stderr (`claude-minimax-proxy.py:212`). The proxy binds to `127.0.0.1` only (`claude-minimax-proxy.py:255`), so it is not reachable from another host.

**Threat model table** (`docs/Claude-Desktop-MiniMax.md:99-107`) explicitly enumerates seven surfaces and asserts none leak the key.

## 6. Operational characteristics

**Ports & processes.** TCP `127.0.0.1:48217`, single Python process (`ThreadingHTTPServer`, thread-per-connection; `claude-minimax-proxy.py:25,255`). The watchdog starts the proxy hidden, capturing stdout/stderr to `AICE_DATA\claude-minimax-proxy.{out,err}` and writing its own log to `AICE_DATA\claude-minimax-proxy.watch.log` (`Watch-ClaudeMiniMaxProxy.ps1:10-27`). Watchdog poll interval is 15 s (`Watch-ClaudeMiniMaxProxy.ps1:55`).

**Upstream timeout.** `urlopen(req, timeout=180)` (`claude-minimax-proxy.py:217`).

**Logging.** `BaseHTTPRequestHandler.log_message` writes method+path+status to stderr (`claude-minimax-proxy.py:110-111`); the proxy adds explicit `[key-path]` lines for key-load diagnostics (`claude-minimax-proxy.py:208,212,214`). No log file is opened by the proxy itself — only by the watchdog wrapper.

**Persistence.** No service is installed by the proxy scripts. The docs reference `ClaudeMiniMaxProxyWatchdog` as an AtLogOn scheduled task (`docs/Claude-Desktop-MiniMax.md:177-179`) but the registration lives outside the audited scripts.

**Recovery.** Watchdog auto-restart on `Get-NetTCPConnection -LocalPort $port -State Listen` failure (`Watch-ClaudeMiniMaxProxy.ps1:14-17,54-61`). `Ctrl+C` in the foreground starter stops the proxy; `Stop-Process -Name python` stops both child and watchdog (`Watch-ClaudeMiniMaxProxy.ps1:6`). Idempotency: re-running the watchdog while already listening exits 0 (`Watch-ClaudeMiniMaxProxy.ps1:40-44`).

## 7. Known limitations visible in code/docs

1. **Hard-coded port 48217** duplicated in three places (`claude-minimax-proxy.py:29`, `Start-ClaudeMiniMaxProxy.ps1:5`, `Watch-ClaudeMiniMaxProxy.ps1:9`) — no single source of truth.
2. **No TLS verification knob.** `urllib.request.Request` is used with default CA trust (`claude-minimax-proxy.py:194,217`); no pinning, no client certs.
3. **No retries, no circuit breaker, no rate limiting.** A single `urlopen` per request (`claude-minimax-proxy.py:217`).
4. **`/v1/messages/count_tokens` returns hard-coded `input_tokens: 0`** (`claude-minimax-proxy.py:170-174`) — admitted in code as "MiniMax does not document this"; usable only as a no-op shim.
5. **Per-request `.env` re-read** on every POST (`claude-minimax-proxy.py:209`) — no in-process key caching.
6. **Watchdog does not enforce that the Python process is *its* proxy.** It only checks `Get-NetTCPConnection -LocalPort $port -State Listen` (`Watch-ClaudeMiniMaxProxy.ps1:14-17`); any other process bound to `48217` would satisfy it.
7. **`Stop-ClaudeMiniMaxProxy.ps1` is documented (`docs/Claude-Desktop-MiniMax.md:44`) but absent** from the audited file list.
8. **`Test-ClaudeMiniMaxSetup.ps1` referenced in the MCP harness doc** (`docs/Claude-Desktop-MCP-E2E-Harness.md:93`) is also absent.
9. **`minimax_env.ps1` and the proxy use inconsistent secret sources** — the proxy reads `MINIMAX_API_KEY` from `G:\private\.env` (or `MINIMAX_KEY`), while `minimax_env.ps1:9-18` reads `minimax_key.txt`/`minimax_api_key.txt` from `C:\Private`, `G:\Private`, or `S:\Private`. They are not interchangeable.
10. **`Harden-MinimaxEnv.ps1` requires elevation** (`docs/Claude-Desktop-MiniMax.md` and inline comment `Harden-MinimaxEnv.ps1:2-6`) but has no self-elevate check; failure is left to the OS.
11. **Registry `inferenceGatewayApiKey` placeholder `"proxy-managed"`** (`Set-ClaudeDesktopInference.ps1:17`) is the only thing visible to Claude Desktop; a user reading the registry would have no indication that the real key is held in `.env`.
12. **CORS allows `*`** for headers and origin on `OPTIONS` (`claude-minimax-proxy.py:122-126`) — acceptable because the listener is loopback-only, but worth noting.
13. **No auth on the proxy itself** beyond loopback bind — any local process can POST and consume MiniMax quota using the injected key (`claude-minimax-proxy.py:209-214`).
14. **Model map is duplicated** between the proxy `MODEL_MAP` (`claude-minimax-proxy.py:93-102`) and the registry `inferenceModels` string (`Set-ClaudeDesktopInference.ps1:20`, `Set-ClaudeDesktopGateway.ps1:23`); changing one without the other causes silent tier drift.