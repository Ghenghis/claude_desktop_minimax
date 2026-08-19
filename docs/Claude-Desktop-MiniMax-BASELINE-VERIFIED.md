# Claude Desktop + MiniMax — VERIFIED WORKING BASELINE

**Status: CONFIRMED WORKING.** Do not modify this setup without creating a new, separate markdown for the change (see `Claude-Desktop-MiniMax-ADVANCED-options.md`).

## What is verified

1. **Automated test suite** (`Test-ClaudeMiniMaxSetup.ps1`) passed all checks on 2026-08-10:
   - Registry `inferenceProvider = gateway`.
   - Registry `inferenceGatewayBaseUrl = http://127.0.0.1:48217/anthropic` (local proxy).
   - Registry `inferenceModels` uses the Anthropic-looking name `claude-sonnet-4-5`, not the raw `MiniMax-M3` string that Claude Desktop's client-side validator rejects.
   - Proxy is listening on port 48217.
   - Proxy `/v1/models` returns an Anthropic-shaped model list.
   - Proxy `/v1/messages` was called directly with `model: claude-sonnet-4-5`; the **actual MiniMax API response** came back with `"model":"MiniMax-M3"` and real generated text.
   - Claude Desktop's own `main.log` showed `ConfigHealth recomputed { state: 'healthy' }` after the config was applied.

2. **Live proof inside Claude Desktop**: when asked directly what model it is, the assistant's own response described itself as **"MiniMax-M3, developed by MiniMax," a global AI foundation model company** — this is the model's own self-identification baked into MiniMax's weights. Anthropic's real Claude models never claim to be MiniMax. This confirms the request is genuinely being served by MiniMax's API using the user's own MiniMax API key, not Anthropic's servers.

## How the working setup is wired

```
Claude Desktop  --(HTTPS, model="claude-sonnet-4-5")-->  Local proxy (127.0.0.1:48217)
                                                              |
                                                    rewrites model -> "MiniMax-M3"
                                                              |
                                                              v
                                         https://api.minimax.io/anthropic/v1/messages
                                         (Auth: X-Api-Key: <user's MiniMax key>)
```

- **Why the proxy exists**: Claude Desktop's client (build `1.26832.0`+) rejects any `inferenceModels` entry whose `name` isn't a recognizable Anthropic model string (error: `"MiniMax-M3" is not an Anthropic model`). The proxy lets Claude Desktop send an accepted name (`claude-sonnet-4-5`) while the real request that reaches MiniMax uses MiniMax's real model ID (`MiniMax-M3`).
- **No protocol translation happens.** MiniMax's endpoint is natively Anthropic-Messages-API-compatible (`https://api.minimax.io/anthropic/v1/messages`), so the proxy only rewrites the `model` field in the JSON body — everything else (headers, streaming, tool calls, content blocks) passes through untouched.
- **Auth**: `X-Api-Key: <MiniMax key>`, loaded at proxy startup from the user's private key folder (`C:\Private`, `G:\Private`, or `S:\Private`), never hardcoded.

## Files that make up this baseline

| File | Purpose |
|---|---|
| `claude-minimax-proxy.py` | The renaming proxy (stdlib only, no dependencies) |
| `Start-ClaudeMiniMaxProxy.ps1` | Starts the proxy; must stay running while using Claude Desktop |
| `Stop-ClaudeMiniMaxProxy.ps1` | Stops the proxy |
| `Set-ClaudeDesktopGateway.ps1` | Writes the registry keys pointing Claude Desktop at the proxy |
| `Test-ClaudeMiniMaxSetup.ps1` | Automated end-to-end verification (rerun this any time to re-confirm health) |
| `minimax_env.ps1` | Loads the MiniMax key from the private folder into env vars |

## Current registry values (as applied)

```text
inferenceProvider          = gateway
inferenceGatewayBaseUrl    = http://127.0.0.1:48217/anthropic
inferenceGatewayAuthScheme = x-api-key
modelDiscoveryEnabled      = true
inferenceModels            = [{"name":"claude-sonnet-4-5","anthropicFamilyTier":"sonnet","supports1m":true}]
```

## Model actually used

The proxy currently maps **every** picker slot to **`MiniMax-M3`** (see `DEFAULT_MINIMAX_MODEL` and `MODEL_MAP` in `claude-minimax-proxy.py`). Regardless of which Anthropic name is shown in the Claude Desktop picker, the request that reaches MiniMax always uses `MiniMax-M3` — MiniMax's flagship, multimodal, 1M-context model.

## What this baseline already supports (no changes needed)

- **Text chat** — fully working, verified above.
- **Vision (image input in chat)** — MiniMax-M3 natively accepts image content blocks over the same Anthropic Messages endpoint the proxy forwards to unmodified. If Claude Desktop's UI lets you attach an image to a message, it will reach M3 exactly as it would reach real Claude, with no proxy changes required. (Not yet manually tested in this session — see `Claude-Desktop-MiniMax-ADVANCED-options.md` for the verification step.)

## What this baseline does NOT support

- Only `MiniMax-M3` is used — you cannot currently pick `MiniMax-M2.7`, `M2.5`, `M2.1`, or `M2` from the Claude Desktop model picker.
- No voice/audio (text-to-speech) — MiniMax's T2A API is a completely separate REST endpoint, unrelated to the Anthropic Messages API that Claude Desktop calls.
- No image or video *generation* (MiniMax `image-01`, Hailuo/H3 video models) — again, separate REST APIs that Claude Desktop's chat UI has no mechanism to call directly.

See `Claude-Desktop-MiniMax-ADVANCED-options.md` for what's technically possible to add and what is a hard client-side limitation.

## Rule going forward

**Do not edit `claude-minimax-proxy.py`, `Set-ClaudeDesktopGateway.ps1`, or the registry to add new features in place.** Any further feature work (multi-model picker, tool-based generation, etc.) must be prototyped and documented separately, and this baseline must remain the fallback if the new work breaks anything.
