# Codex Desktop + MiniMax

## Paid plan stays the default

Codex Desktop reads the same `~/.codex/config.toml` as the Codex CLI. The existing config keeps the paid OpenAI/Codex plan:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"
service_tier = "priority"
```

This means Codex Desktop starts on the paid $200/month plan.

## MiniMax backup provider

A `minimax` provider block was added to `~/.codex/config.toml`:

```toml
[model_providers.minimax]
name = "MiniMax"
base_url = "https://api.minimax.io/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "responses"
```

A backup profile was created at `~/.codex/minimax.config.toml`:

```toml
model = "MiniMax-M3"
model_provider = "minimax"
model_context_window = 1000000

[model_providers.minimax]
name = "MiniMax"
base_url = "https://api.minimax.io/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "responses"
```

## How to use

- Run `Start-CodexDesktop.ps1` to open Codex Desktop on the paid plan.
- Run `Start-CodexDesktop-Backup.ps1` to open Codex Desktop on MiniMax when the paid plan runs out.

## MiniMax features in Codex Desktop

Codex Desktop can use the local gateway for chat (`MiniMax-M3`) and the `minimax-media` MCP server for media features:

- Chat / text: `POST /v1/responses` -> `MiniMax-M3`
- Speech / TTS: `POST /v1/audio/speech` -> `MiniMax T2A v2` (`speech-2.8-hd`)
- Image generation: `POST /v1/images/generations` -> `image-01`
- Image, speech, and video tools: `minimax_generate_speech`, `minimax_generate_image`, `minimax_generate_video` via the `minimax-media` MCP server

Enable the `minimax-media` MCP server in `~/.codex/config.toml`:

```toml
[mcp_servers.minimax-media]
command = "powershell"
args = ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "G:\\Github\\Testing-Claude-Minimax-Mcp\\minimax-mcp-server\\Start-MinimaxMediaMcp.ps1"]
enabled = true
startup_timeout_sec = 30
```

When a feature or model is not supported, the gateway returns a `MiniMax error` and blocks the request; it never silently falls back to OpenAI.

Sources:
- https://platform.minimax.io/docs/token-plan/codex-cli
- https://developers.openai.com/codex/config-advanced
