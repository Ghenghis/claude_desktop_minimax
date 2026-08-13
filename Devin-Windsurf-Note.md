# Devin / Windsurf MiniMax Note

Devin Desktop and Windsurf do not currently expose a native "custom OpenAI-compatible model provider" field for Cascade.

Their BYOK (bring-your-own-key) support is limited to Anthropic, OpenAI, and similar first-class providers. There is no documented way to point Cascade at `https://api.minimax.io`.

Options:
1. Use Devin/Windsurf's built-in model picker as-is.
2. If using Windsurf, install the **Roo Code** extension and configure an OpenAI-compatible provider pointing at `https://api.minimax.io/v1` with the MiniMax API key from your private folder.
3. Use Claude Code / Claude Desktop / Codex for the MiniMax-backed agent workflows.
