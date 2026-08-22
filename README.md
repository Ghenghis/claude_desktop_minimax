# MiniMax setup for Claude Desktop, Codex Desktop, and Devin/Windsurf (Windows)

MiniMax keys are kept only in a private folder. The loader searches `C:\Private`, `G:\Private`, `S:\Private` and uses the first one it finds.

## Files created in the private folder
- `minimax_key.txt` — MiniMax token for Claude Desktop (Anthropic-compatible)
- `minimax_api_key.txt` — MiniMax API key for Codex (OpenAI-compatible)

## Detailed docs

- `docs/Claude-Desktop-MiniMax.md` — Claude Desktop + MiniMax M3 setup (working)
- `docs/Codex-Desktop-MiniMax.md` — paid plan + MiniMax backup profile
- `docs/Devin-Windsurf-MiniMax.md` — current support status

## Current status

1. **Claude Desktop** — working via the `claude-minimax-v2` Anthropic-compatible gateway.
   - The gateway (`claude-minimax-v2/gateway/`) accepts Anthropic Messages API calls, maps Claude-family aliases to MiniMax models, and forwards to `https://api.minimax.io/anthropic/v1/messages`.
   - Registry: `HKCU:\SOFTWARE\Policies\Claude` with `inferenceGatewayBaseUrl = http://127.0.0.1:<port>/anthropic`.
   - The actual `<port>` is auto-discovered (defaults to `48217`, falls back to a free OS port) and written to `claude-minimax-v2/.port`.
   - `inferenceModels` uses Claude-style IDs (`claude-sonnet-4-5`, etc.) with `labelOverride` so the picker displays `MiniMax M3`, `MiniMax M2.7`, etc.  This is required because Claude Desktop rejects non-Anthropic model names.

2. **ChatGPT Codex** — working via the OpenAI Responses API.
   - `~/.codex/config.toml` uses `model = "MiniMax-M3"`, `model_provider = "minimax_gateway"`, and `wire_api = "responses"`.
   - The `claude-minimax-proxy.py` legacy proxy translates `POST /v1/responses` to `POST /v1/chat/completions` and back.

3. **Devin / Windsurf** — no guaranteed native way to redirect Cascade to a custom OpenAI-compatible endpoint. See `docs/Devin-Windsurf-MiniMax.md` for ACP/Roo Code alternatives.

### Other clients that work with this gateway

| Client | Override location |
|---|---|
| **Continue.dev** | `~/.continue/config.json` `apiBase` |
| **Cline** | VS Code settings `cline.modelSettings.*.apiUrl` |
| **Kilo Code** | `openai.baseUrl` in settings |

They all point at `http://127.0.0.1:<port>/v1` and pass the MiniMax key as `Authorization: Bearer <token>`.

## Current C: runtime (active)

The supported runtime is pinned to `C:\Users\Admin\claude-codex-devin` so
Claude and Codex do not depend on removable or unavailable `G:`/`S:` drives.

| Client | Service | Endpoint |
|---|---|---|
| Claude Desktop | `claude-minimax-proxy` | `http://127.0.0.1:48217/anthropic` |
| Codex Desktop | `api2codex-minimax` | `http://127.0.0.1:48218/v1` |
| Both | `mini` MCP orchestrator | shared stdio connection |

Claude aliases route truthfully: Sonnet → `MiniMax-M3`, Opus → `MiniMax-M2.7`,
Haiku → `MiniMax-M2.7-highspeed`. Codex uses
`C:\Users\Admin\.codex\model-catalogs\minimax-catalog.json` for the MiniMax
model picker.

Both clients receive the shared MiniMax MCP capability set through `mini`:

- `minimax`: speech, voices, voice clone/design, playback, image, video, and video query
- `minimax-media`: speech, image, video, music, file retrieval, and Video Agent task tools
- `minimax-coding-plan`: `web_search` and `understand_image`
- `touchpoint`: Windows UI Automation/CDP inspection and interaction
- `winremote`: Windows inspection tools; Tier 2 and Tier 3 disabled by default
- `Windows-MCP` and `daves-tools-harness`

Generated media is stored at `C:\Users\Admin\MiniMax-Generated`.
Run the repairable health check after boot or whenever a client reports a
connection problem:

```powershell
powershell -ExecutionPolicy Bypass -NoProfile -File C:\Users\Admin\claude-codex-devin\Test-MiniMaxStack.ps1 -Fix
```

The harness checks both gateways, every Claude model tier, the Codex catalog,
registry routing, MCP handshakes, and the Claude package-locking service.

## Codex Desktop permissions

Codex Desktop can expose `Bypass Permissions` / `Full access` for trusted local
projects. Its UI state is stored in
`C:\Users\Admin\.codex\.codex-global-state.json`. This mode removes local
sandbox restrictions and approval prompts; it does not enable WinRemote Tier 3.
Use it only for trusted workspaces. See `AGENTS.md` for the repair and the
security trade-off.

## Quick start for Claude Desktop (one-touch)

Make sure the sibling folders exist:

```text
G:\Github\claude-codex-devin
G:\Github\claude-minimax-v2
```

For an always-connected Hermes workspace (survives `G:`/`S:` drive disconnects), copy or clone `claude-codex-devin` to `C:\Users\Admin\claude-codex-devin` and set `MCP_LOCK_WORKSPACE` to that path in your MCP config.

Place the MiniMax API key in `S:\private\minimax_key.txt` (plain text, one line) for fastest access. The loader falls back to `G:\private\minimax_key.txt`, then `MINIMAX_API_KEY` in `S:\private\.env` or `G:\private\.env`.

Then run:

```powershell
# Start the gateway and wire the registry
C:\Users\Admin\claude-codex-devin\Start-ClaudeMinimaxV2.ps1

# Restart Claude Desktop when the script says so.
```

To stop the gateway later, run `Stop-MinimaxGateway.ps1`.

If anything feels off, the idempotent `Repair-ClaudeMinimaxV2.ps1` stops the gateway, validates Python compiles, and restarts/wires everything.

See `docs/E2E-Blueprint.md` for request flows, `docs/Claude-Desktop-MiniMax.md` for the model-picker details, and `docs/Codex-Setup-Audit.md` for historical fixes.

## Portable Windows 11 install (Phase 5)

For a clean Windows 11 PC:

1. Build: `G:\Github\claude-codex-devin\portable\Build-PortableZip.ps1`
2. Distribute: `G:\Github\claude-minimax-v2-portable.zip`
3. On the target PC, extract the zip, place the key in `S:\private\minimax_key.txt` (or `G:\private` or `C:\private`), and double-click `start-here.bat`.

See `docs/diagrams/Portability.md` for the bundle layout and `docs/diagrams/MCP-Gap.md` for the media MCP wiring.

## Real gaps / release hardening

Run `Fix-RealGaps.ps1` to close the known unconfigured items (OpenHands bridge, provider registry, browser launch target, `glab` install, etc.):

```powershell
G:\Github\claude-codex-devin\Fix-RealGaps.ps1
```

`Fix-RealGaps.ps1` now defaults to the always-connected `C:\Users\Admin\claude-codex-devin` Hermes workspace and creates a populated `provider_registry.json`.

See `docs/REAL-GAPS.md` for the full audit.

If you need the GitLab token for `glab` / Hermes, run `Set-GitLabToken.ps1` with your token in `S:\private\glab_token.txt` or `G:\private\glab_token.txt`.

## Windsurf / Devin MCP support

The live Windsurf MCP config is at `C:\Users\Admin\.codeium\windsurf\mcp_config.json`:

- `hermes3d-locks` env points to `C:\Users\Admin\claude-codex-devin` (always-connected workspace)
- `HERMES_AGENT_ENABLED=1` and `OPENHANDS_URL` enable the Hermes Agent bridge
- `HERMES_PROVIDER_REGISTRY` points to `C:\Users\Admin\claude-codex-devin\.hermes3d_orchestrator\provider_registry.json`
- `GITLAB_TOKEN` / `GLAB_TOKEN` are loaded from `S:\private\glab_token.txt`

For initial Windsurf setup, run:

```powershell
G:\Github\claude-codex-devin\windsurf\Install-WindsurfMcpConfig.ps1
```

This writes `minimax-media` into `C:\Users\<you>\mcp_config.json` with the correct `python.exe` and `server.py` paths, so the `transport closed` problem does not reappear.

