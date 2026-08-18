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

## Quick start for Claude Desktop (one-touch)

Make sure the sibling folders exist:

```text
G:\Github\claude-codex-devin
G:\Github\claude-minimax-v2
```

Place the MiniMax API key in `G:\private\minimax_key.txt` (plain text, one line). The loader falls back to `MINIMAX_API_KEY` in `G:\private\.env` if the key file is missing.

Then run:

```powershell
# Start the gateway and wire the registry
G:\Github\claude-codex-devin\Start-ClaudeMinimaxV2.ps1

# Restart Claude Desktop when the script says so.
```

To stop the gateway later, run `Stop-MinimaxGateway.ps1`.

If anything feels off, the idempotent `Repair-ClaudeMinimaxV2.ps1` stops the gateway, validates Python compiles, and restarts/wires everything.

See `docs/E2E-Blueprint.md` for request flows, `docs/Claude-Desktop-MiniMax.md` for the model-picker details, and `docs/Codex-Setup-Audit.md` for historical fixes.
