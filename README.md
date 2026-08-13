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
   - Claude Desktop rejects the non-Anthropic model name `MiniMax-M3` in `inferenceModels`.
   - A tiny Python proxy (`claude-minimax-proxy.py`) accepts Anthropic-looking names from Claude Desktop, rewrites `claude-sonnet-4-5` to `MiniMax-M3`, and forwards the request unchanged to `https://api.minimax.io/anthropic/v1/messages`.
   - The proxy has been started and verified end-to-end with a real MiniMax response.
   - Steps:
     1. Run `Start-ClaudeMiniMaxProxy.ps1` (keep the window open).
     2. Restart Claude Desktop and choose the third-party gateway option.
     3. Send a test message.

2. **Codex Desktop** — paid plan is the default; MiniMax backup profile exists.
   - `Start-CodexDesktop.ps1` — opens Codex Desktop on the paid plan.
   - `Start-CodexDesktop-Backup.ps1` — opens Codex Desktop on MiniMax when the paid quota runs out.

3. **Devin / Windsurf** — no guaranteed native way to redirect Cascade to a custom OpenAI-compatible endpoint. See `docs/Devin-Windsurf-MiniMax.md` for ACP/Roo Code alternatives.

## Quick start for Claude Desktop

```powershell
# 1. Start the proxy (keep this window open)
C:\github\claude-codex-devin\Start-ClaudeMiniMaxProxy.ps1

# 2. Restart Claude Desktop and use the third-party gateway option.
```

To stop the proxy later, run `Stop-ClaudeMiniMaxProxy.ps1`.
