# Claude/Codex + MiniMax Gateway Runbook

## Architecture

| Client | Gateway | URL | Purpose |
|--------|---------|-----|---------|
| Claude Desktop | `claude-minimax-proxy` (Windows service) | `http://127.0.0.1:48217/anthropic` | Anthropic Messages API → MiniMax |
| Codex | `api2codex` (Windows service) | `http://127.0.0.1:48218/v1` | OpenAI Responses API → MiniMax |
| Claude + Codex | `mini` (daemon) | `C:\Users\Admin\.mini` | Single on-demand MCP orchestrator |

All gateways and scripts are pinned to `C:\` for stability. The `G:\Github\claude-codex-devin` path is a backup; use `C:\Users\Admin\claude-codex-devin` for active work.

## Important Paths

- Project root: `C:\Users\Admin\claude-codex-devin`
- Secrets: `C:\private\.env`, `C:\private\.proxy-token`
- Claude registry: `HKCU:\SOFTWARE\Policies\Claude`
- WinSW services live next to their XML files in the project root
- `api2codex`: `C:\Users\Admin\claude-codex-devin\api2codex.py`
- `claude-minimax-proxy`: `C:\Users\Admin\claude-codex-devin\claude-minimax-proxy.py`

## Windows Services

| Service | ID | Port | Status |
|---------|----|------|--------|
| `LiteLLM Claude Gateway` | `litellm-claude` | 48219 | **Disabled** (startup hangs, see below) |
| `Claude MiniMax Anthropic Gateway` | `claude-minimax-proxy` | 48217 | **Active** |
| `api2codex MiniMax Codex Gateway` | `api2codex` | 48218 | **Active** |

Service commands (run in project root):

```powershell
# claude-minimax-proxy
& 'C:\Users\Admin\claude-codex-devin\claude-minimax-proxy-service.exe' start
& 'C:\Users\Admin\claude-codex-devin\claude-minimax-proxy-service.exe' stop

# api2codex
& 'C:\Users\Admin\claude-codex-devin\api2codex-service.exe' start
& 'C:\Users\Admin\claude-codex-devin\api2codex-service.exe' stop

# LiteLLM
& 'C:\Users\Admin\claude-codex-devin\litellm-service.exe' start
& 'C:\Users\Admin\claude-codex-devin\litellm-service.exe' stop
```

## Quick Switcher

`Switch-ClaudeGateway.ps1` toggles Claude between the custom proxy and LiteLLM:

```powershell
# Current / stable path
.\Switch-ClaudeGateway.ps1 -Mode Proxy

# Experimental LiteLLM path
.\Switch-ClaudeGateway.ps1 -Mode LiteLLM
```

After switching, **restart Claude Desktop**.

## Post-reboot Checklist

1. If `CoworkVMService` (display name `Claude`) starts automatically, it will lock the `WindowsApps\Claude_*` package. Stop it and, as an admin, set it to Manual:

   ```powershell
   Stop-Service -Name CoworkVMService -Force
   sc config CoworkVMService start= demand   # requires admin
   ```

2. Verify the desired gateway service is running:

   ```powershell
   sc query claude-minimax-proxy
   sc query api2codex
   ```

3. Test the endpoints:

   ```powershell
   # Claude
   $token = (Get-Content -LiteralPath 'C:\private\.proxy-token' -Raw).Trim()
   $headers = @{'X-Api-Key'=$token;'anthropic-version'='2023-06-01';'Content-Type'='application/json'}
   $body = '{"model":"claude-sonnet-4-5","max_tokens":100,"messages":[{"role":"user","content":"hello"}]}'
   Invoke-WebRequest -Uri 'http://127.0.0.1:48217/anthropic/v1/messages' -Method POST -Headers $headers -Body $body -TimeoutSec 60 -UseBasicParsing

   # Codex
   $body = '{"model":"MiniMax-M3","input":[{"role":"user","content":[{"type":"input_text","text":"hello"}]}],"max_output_tokens":100, "stream": false}'
   Invoke-WebRequest -Uri 'http://127.0.0.1:48218/v1/responses' -Method POST -Headers @{'Content-Type'='application/json'; 'Authorization'='Bearer any'} -Body $body -TimeoutSec 60 -UseBasicParsing
   ```

## Known Issues

### LiteLLM startup hang
`LiteLLM 1.97.0` installs `fastapi 0.141.1`, but that version removed `get_flat_dependant`; `fastapi` was downgraded to `0.136.3` to allow `LiteLLM` to start. Even then, the Windows `litellm.exe` proxy can hang during startup and never bind to port `48219` (no `Uvicorn running` line). It appears related to an `InquirerPy` / interactive master-key prompt and/or very slow package imports.

**Status:** `LiteLLM` service is disabled for now. To continue the LiteLLM experiment after reboot, try launching with an explicit master key and without interactivity:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
$env:MINIMAX_API_KEY = (Get-Content 'C:\private\.env' -Raw | Select-String '^MINIMAX_API_KEY=(.*)$').Matches.Groups[1].Value.Trim()
$master = (Get-Content 'C:\private\.proxy-token' -Raw).Trim()
& 'C:\Python314\Scripts\litellm.exe' --config 'C:\Users\Admin\claude-codex-devin\litellm_config.yaml' --port 48219 --api-key $master
```

If `LiteLLM` cannot be stabilized, the custom `claude-minimax-proxy` is the known-working fallback.

### `CoworkVMService` locking Claude package
`CoworkVMService` is a background component of the Claude `WindowsApps` package. When it is `Running` and `Automatic`, launching Claude Desktop can fail with `Another program is currently using this file`. Stop the service and set it to `Manual`.

### `mini` MCP timeout
`mini` starts on demand when a client connects. If some MCPs show `context deadline exceeded` on `mini status`, only the active servers matter for the current chat. `daves-tools-harness` is fixed and exposes its orchestrator tools; other servers must be reachable on their own.

### `mini` env blocks break Python servers
The `env:` list in a `~/.mini/servers/*.yaml` replaces the child environment
instead of merging it. Python MCP servers then crash at startup
(`Path.home()` needs `USERPROFILE`) and mini reports `MCP handshake:
connection closed`. Do NOT add `env:` to Python-based servers; let them
self-locate secrets (both MiniMax servers read `C:\private\.env` themselves).

## MiniMax media tools (both chat UIs, via mini)

| Server | Source | Tools |
|---|---|---|
| `minimax` (official MiniMax-MCP) | isolated venv `venvs\minimax-mcp`, launched by `minimax-mcp-official.cmd` | `text_to_audio`, `list_voices`, `voice_clone`, `voice_design`, `play_audio`, `text_to_image`, `generate_video`, `query_video_generation` |
| `minimax-media` (custom) | `minimax-mcp-server\server.py` | `minimax_generate_speech`, `minimax_generate_image`, `minimax_generate_video`, `minimax_generate_music` |
| `minimax-coding-plan` | isolated venv `venvs\minimax-plan`, launched by `minimax-coding-plan-mcp.cmd` | `web_search`, `understand_image` |

- Generated files land in `C:\Users\Admin\MiniMax-Generated`.
- The official server needs `MINIMAX_API_KEY`; the launcher `.cmd` loads it
  from `C:\private\.env` (never hardcode the key in configs).
- The official package (`minimax-mcp`) requires `mcp>=2.0`, which conflicts
  with litellm and the custom server (`mcp 1.x`) — hence the isolated venv.
  Keep `C:\Python314` on `mcp==1.28.1`.
- Music Generation API is discontinued for new MiniMax users (2026-08-20).
- Codex model picker: `model_catalog_json` in `~/.codex/config.toml` points to
  `~/.codex/model-catalogs/minimax-catalog.json` (M3, M2.7, M2.7-highspeed).
  If the Desktop picker hides them, known workaround: block `ab.chatgpt.com`
  in hosts, delete WebView `Local Storage\leveldb`, restart (upstream issues
  openai/codex#19694, #37379).

## Codex Desktop permission mode

Codex Desktop was hiding `Full access` / `Bypass Permissions` because
`.codex-global-state.json` had `composer-permission-mode-visibility.full-access`
set to false and the local mode was `guardian-approvals`. The local Codex UI
state was changed to expose and select `full-access`; the JSON was parsed
successfully after the edit. Fully exit and relaunch Codex Desktop for the UI
to reload it. This affects local shell/file sandbox approvals only; MCP Tier 3
remains disabled.

This mode removes local sandbox restrictions and approval prompts. Use it only
for trusted projects. If the UI still shows the old mode, close every
`ChatGPT.exe` process, relaunch Codex, and inspect the composer permission menu.

## 24/7 health harness

`Test-MiniMaxStack.ps1` checks secrets, both gateway services, all three
Claude model tiers (verifies each alias reaches its MiniMax model), the Codex
gateway + catalog, the Claude registry, mini MCP servers, and that
`CoworkVMService` isn't locking the Claude package. `-Fix` restarts anything
that's down. Runs every 30 min + at logon via scheduled tasks
`MiniMaxStack-Health` / `MiniMaxStack-Health-Logon`; log at
`logs\minimax-stack-health.log`.

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Admin\claude-codex-devin\Test-MiniMaxStack.ps1 -Fix
```
