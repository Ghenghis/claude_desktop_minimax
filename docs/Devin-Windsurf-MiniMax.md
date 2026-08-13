# Devin / Windsurf + MiniMax

## Current status

There is **no documented native setting** in Devin Desktop or Windsurf that lets you point the built-in Cascade agent at an arbitrary OpenAI-compatible endpoint.

- Windsurf's public docs cover Cascade model selection, Devin Local, usage/credit accounting, and MCP servers, but **not** a custom LLM base URL for Cascade itself.
- Devin Desktop's admin docs let you filter by model/provider, but only among first-class providers (Anthropic, OpenAI, Google, etc.).

Sources:
- https://flatkey.ai/blog/windsurf-openai-compatible-api-setup-flatkey
- https://docs.devin.ai/desktop/cascade/mcp
- https://docs.devin.ai/desktop/guide-for-admins

## What does work with Windsurf

If your specific Windsurf build exposes a **Custom / OpenAI-compatible provider** field in Settings, you can paste:

```text
Base URL: https://api.minimax.io/v1
API key: <from C:\Private\minimax_api_key.txt>
Model:    MiniMax-M3
```

This is build-dependent. If the field is missing, the only other route is installing the **Roo Code** extension, which supports a 3rd-party OpenAI-compatible provider.

Source:
- https://docs.kimchi.dev/docs/windsurf
- https://github.com/vivian254338489/tken-cursor-windsurf-base-url-guide

## Bottom line

Devin/Windsurf cannot be forced to use MiniMax through any official, guaranteed setting today. Claude Desktop and Codex Desktop are the tools that can reliably route to MiniMax.
