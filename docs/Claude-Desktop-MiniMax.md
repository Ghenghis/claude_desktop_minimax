# Claude Desktop + MiniMax

## What works today

Claude Desktop on Windows supports third-party inference through a **Gateway** provider. The official docs say you enable it via `Help -> Troubleshooting -> Enable Developer Mode`, then `Developer -> Configure Third-Party Inference`.

Sources:
- https://claude.com/docs/third-party/claude-desktop/in-app-configuration
- https://claude.com/docs/third-party/claude-desktop/gateway

## The model-name blocker

Starting with Claude Desktop `1.6259.1`, the client validates every entry in `inferenceModels` and rejects any model name that is not recognizably Anthropic.

Error seen on this machine:
```json
{
  "state": "invalid_config",
  "failingField": "inferenceModels",
  "message": "Invalid custom3p managed config: inferenceModels: configured model \"MiniMax-M3\" is not an Anthropic model. Gateway deployments require an Anthropic model from the provider catalog — expected a gateway model route referencing an Anthropic model (e.g. claude-sonnet-4-5, anthropic/claude-*). Name routes to match the underlying model.",
  "clientVersion": "1.26832.0"
}
```

This validation is client-side. The CLI (`claude`) is **not** affected.

Source: https://github.com/anthropics/claude-code/issues/56990

## Working setup: local model-renaming proxy

Because Claude Desktop refuses to send `MiniMax-M3` as a model name, we run a tiny local proxy that:

1. Accepts Anthropic-looking model names from Claude Desktop (e.g. `claude-sonnet-4-5`).
2. Rewrites the `model` field to `MiniMax-M3`.
3. Forwards the request unchanged to `https://api.minimax.io/anthropic/v1/messages`.

This is the same pattern used by `github.com/francescogruner/claude-3p-ollama-proxy` for other non-Anthropic gateways.

### Files created

- `claude-minimax-proxy.py` — the proxy (Python 3, no external dependencies).
- `Start-ClaudeMiniMaxProxy.ps1` — starts the proxy.
- `Stop-ClaudeMiniMaxProxy.ps1` — stops the proxy.
- `Set-ClaudeDesktopGateway.ps1` — points Claude Desktop at the proxy.

### Registry config applied by `Set-ClaudeDesktopGateway.ps1`

```text
inferenceProvider          = gateway
inferenceGatewayBaseUrl    = http://127.0.0.1:48217/anthropic
inferenceGatewayApiKey     = <from C:\Private\minimax_key.txt>
inferenceGatewayAuthScheme = x-api-key
modelDiscoveryEnabled      = true
inferenceModels            = [{"name":"claude-sonnet-4-5","anthropicFamilyTier":"sonnet","supports1m":true}]
```

The proxy listens on `127.0.0.1:48217`, serves `/v1/models` for discovery, and rewrites `/v1/messages` model names before forwarding to MiniMax.

## How to start

1. Open a PowerShell window and keep it open:
   ```powershell
   C:\github\claude-codex-devin\Start-ClaudeMiniMaxProxy.ps1
   ```
2. Restart Claude Desktop.
3. The sign-in screen should offer the third-party gateway option; select it.
4. Send: `Respond with exactly: MiniMax M3 connection successful.`
5. Test tool calls: ask it to create a folder `minimax-claude-test` with a `README.md` inside containing the model name and date.

## Verification without a terminal

1. `Help -> Troubleshooting -> Copy Managed Configuration Report` — confirms provider detected + credentials valid (secrets redacted).
2. If anything fails, check `%LOCALAPPDATA%\Claude-3p\Logs\main.log`.

## Verified test results

The proxy was started and tested locally:

- `GET http://127.0.0.1:48217/anthropic/v1/models` returns the expected Anthropic-shaped model list.
- `POST http://127.0.0.1:48217/anthropic/v1/messages` with model `claude-sonnet-4-5` was forwarded to MiniMax as `MiniMax-M3` and returned a real assistant response.

## Secure key handling (G:\private\.env)

The proxy loads `MINIMAX_API_KEY` from `G:\private\.env` at startup and holds
it in process memory only. The value is never printed, logged, or written to
disk by any of the scripts.

### Files

| File | Role |
|------|------|
| `Load-MinimaxKey.ps1` | Reads `G:\private\.env`, sets `$env:MINIMAX_API_KEY` in this process only |
| `claude-minimax-proxy.py` | Parses `.env` (`KEY=value`, quotes, `#` comments) and **always overrides** any client-supplied auth with the real key (see "Credential override" below) |
| `Test-MinimaxEnvACL.ps1` | Reports file size, owner, and key-line length — never the key itself |
| `Start-ClaudeMiniMaxProxy.ps1` | Dot-sources `Load-MinimaxKey.ps1`, then runs the proxy |

### Threat model — what is and isn't exposed

| Surface | Exposed? | Why |
|---|---|---|
| Chat / prompts | No | The key is never typed, pasted, or referenced |
| PowerShell command history | Only file paths | The `.ps1` wrappers set env vars via dot-sourcing; the value never appears on a command line |
| Proxy stdout / stderr | No | `log_message` only logs method + path + status; headers and bodies are never printed |
| `%LOCALAPPDATA%\Claude-3p\Logs\main.log` | No | Claude Desktop only sees the loopback proxy URL; the real key never reaches its registry entry |
| Windows registry (`inferenceGatewayApiKey`) | No (placeholder) | Set the registry value to any non-empty placeholder (e.g. `proxy-managed`); the proxy ignores Claude Desktop's header and uses the `.env` value |
| Persistent environment variables | No | `Load-MinimaxKey.ps1` uses `$env:MINIMAX_API_KEY = ...` (process scope). It never calls `[Environment]::SetEnvironmentVariable` |
| Disk beyond `G:\private\.env` | No | The proxy never writes the key |

### One-time setup

```powershell
# 1. Restrict the .env to your account only. Deny Everyone.
$acl = Get-Acl 'G:\private\.env'
$acl.SetAccessRuleProtection($true, $false)   # disable inheritance, copy current rules
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $env:USERNAME, 'Read', 'Allow')
$acl.AddAccessRule($rule)
$deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
    'Everyone', 'FullControl', 'Deny')
$acl.AddAccessRule($deny)
Set-Acl 'G:\private\.env' $acl

# 2. Verify (never prints the key):
powershell -NoProfile -File G:\Github\claude-codex-devin\Test-MinimaxEnvACL.ps1

# 3. Make sure the .env line is exactly:
#    MINIMAX_API_KEY=<your-key>
#    (quotes around the value are optional; # comments are allowed)
```

### Daily use

```powershell
# Keep this window open while using Claude Desktop.
G:\Github\claude-codex-devin\Start-ClaudeMiniMaxProxy.ps1
```

### Claude Desktop registry — what to put there

`Set-ClaudeDesktopInference.ps1` writes the literal string `proxy-managed`
to `inferenceGatewayApiKey`. Claude Desktop only needs a non-empty value to
pass its own validation; the proxy ignores what Claude sends and **always**
injects the real `MINIMAX_API_KEY` from `G:\private\.env` itself. See the
"Credential override" section below.

```powershell
Set-ClaudeDesktopInference.ps1
```

Verify the registry:

```powershell
powershell -NoProfile -Command "Get-ItemProperty 'HKCU:\SOFTWARE\Policies\Claude' | Select-Object inferenceProvider,inferenceGatewayBaseUrl,inferenceGatewayApiKey"
# expect: gateway / http://127.0.0.1:48217/anthropic / proxy-managed
```

### Credential override (always inject the .env key)

The proxy **discards** every `Authorization` and `X-Api-Key` header the
client supplies and replaces them with the real key from `G:\private\.env`.
This is intentional: Claude Desktop's gateway credential is always a
placeholder string (e.g. `proxy-managed`); forwarding it to MiniMax causes
HTTP 401 with body `{"type":"error","error":{"type":"authentication_error","message":"login fail: Please carry the API secret key in the 'X-Api-Key' field of the request header"}}`.

The proxy logs which path fired to stderr:

```
[key-path] client supplied auth header -- discarding and injecting MINIMAX_API_KEY from .env
[key-path] injected X-Api-Key from .env (len=125)
13/Aug/2026 01:11:05 "POST /anthropic/v1/messages HTTP/1.1" 200 -
```

Never the key value — only its byte length.

### Auto-restart watchdog

`Watch-ClaudeMiniMaxProxy.ps1` is registered as the scheduled task
`ClaudeMiniMaxProxyWatchdog` (AtLogOn trigger, restart on crash). On every
logon the proxy is brought back up automatically.

### One-line status check

```powershell
# proxy alive?
Get-NetTCPConnection -LocalPort 48217 -State Listen

# registry wired?
Get-ItemProperty 'HKCU:\SOFTWARE\Policies\Claude' | Select-Object inferenceProvider,inferenceGatewayBaseUrl

# .env readable?  (lengths only, never the key)
powershell -NoProfile -File G:\Github\claude-codex-devin\Test-MinimaxEnvACL.ps1

# end-to-end live probe (Authorization: Bearer proxy-managed simulates Claude Desktop)
Invoke-WebRequest -Uri 'http://127.0.0.1:48217/anthropic/v1/messages' -Method POST `
  -ContentType 'application/json' `
  -Headers @{ Authorization = 'Bearer proxy-managed'; 'anthropic-version' = '2023-06-01' } `
  -Body '{"model":"claude-haiku-4-5","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
# expect: StatusCode 200, body contains "MiniMax-M2.1"  (haiku -> M2.1)
```

### If you suspect the key leaked

1. Revoke the key in the MiniMax console and issue a new one.
2. Replace `MINIMAX_API_KEY=...` in `G:\private\.env` (use a script that reads
   from your password manager or a clipboard paste in a terminal that does not
   log commands — never paste it into chat).
3. Restart the proxy window.
4. Re-run `Test-MinimaxEnvACL.ps1` to confirm ACL is still restrictive.

## Direct MiniMax (no proxy)

You can try the direct config by editing `Set-ClaudeDesktopGateway.ps1` back to:

```text
inferenceGatewayBaseUrl = https://api.minimax.io/anthropic
inferenceModels         = [{"name":"MiniMax-M3","anthropicFamilyTier":"opus","supports1m":true}]
```

If your Claude Desktop build accepts that, the proxy is unnecessary. As of the version that produced the error above, it does not.

## Alternative fallback: CCPG or LiteLLM

If you prefer a maintained third-party gateway instead of the small Python proxy:

- **CCPG** (`ccpg.live` / `github.com/danielalves96/claude-code-provider-gateway`) — Windows desktop app with MiniMax as a built-in supported provider.
- **LiteLLM** — run `litellm --config litellm_config.yaml` with a model mapping such as `claude-sonnet-4-5 -> openai/MiniMax-M3` at `https://api.minimax.io/v1`.

Sources:
- https://www.truefoundry.com/docs/ai-gateway/claude-desktop
- https://docs.zenmux.ai/best-practices/claude-desktop
- https://cc-relay.ai/en/docs/providers/
