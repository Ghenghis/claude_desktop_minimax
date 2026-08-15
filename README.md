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

1. **Claude Desktop** — working via a local model-renaming proxy.
   - The proxy (`claude-minimax-proxy.py`) accepts Anthropic-looking names from Claude Desktop, rewrites `claude-sonnet-4-5` to `MiniMax-M3`, and forwards the request to `https://api.minimax.io/anthropic/v1/messages`.
   - Registry: `HKCU:\SOFTWARE\Policies\Claude` with `inferenceGatewayBaseUrl = http://127.0.0.1:48217/anthropic`.

2. **ChatGPT Codex** — working via the OpenAI Responses API.
   - `~/.codex/config.toml` uses `model = "MiniMax-M3"`, `model_provider = "minimax_gateway"`, and `wire_api = "responses"`.
   - The proxy translates `POST /v1/responses` to `POST /v1/chat/completions` and back.

3. **Devin / Windsurf** — no guaranteed native way to redirect Cascade to a custom OpenAI-compatible endpoint. See `docs/Devin-Windsurf-MiniMax.md` for ACP/Roo Code alternatives.

### Other clients that work with this gateway

| Client | Override location |
|---|---|
| **Continue.dev** | `~/.continue/config.json` `apiBase` |
| **Cline** | VS Code settings `cline.modelSettings.*.apiUrl` |
| **Kilo Code** | `openai.baseUrl` in settings |

They all point at `http://127.0.0.1:48217/v1` and pass the proxy token as `Authorization: Bearer <token>`.

## Quick start for Claude Desktop

```powershell
# 1. Start the proxy (keep this window open)
C:\github\claude-codex-devin\Start-ClaudeMiniMaxProxy.ps1

# 2. Restart Claude Desktop and use the third-party gateway option.
```

To stop the proxy later, run `Stop-ClaudeMiniMaxProxy.ps1`.

See `docs/E2E-Blueprint.md` for the full request flows and `docs/Codex-Setup-Audit.md` for the issues that were fixed.
