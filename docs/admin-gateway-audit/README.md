# Admin Gateway — Audit Bundle

Six documents produced by layered agent audits of the user's local third-party inference gateway (`claude-minimax-proxy.py` + supporting PowerShell scripts in `G:\Github\claude-codex-devin`).

## Documents

1. **[01-current-features.md](./01-current-features.md)** — overview, current feature inventory, architecture, configuration surface, security posture, operational characteristics, and known limitations. Every claim cites `file:line`.
2. **[02-competitive-analysis.md](./02-competitive-analysis.md)** — audit of LiteLLM, Portkey, Cloudflare AI Gateway, OpenRouter, TrueFoundry, Kong AI Gateway, Tyk, Envoy AI Gateway, ZenMux, CCPG, and `claude-3p-ollama-proxy`, with a feature matrix and a "what every serious gateway has that the user's doesn't" synthesis.
3. **[03-feature-recommendations.md](./03-feature-recommendations.md)** — prioritized P0/P1/P2 feature list with rationale, effort, implementation sketch, risks, and a one-weekend MVP order.
4. **[04-minimax-extension-roadmap.md](./04-minimax-extension-roadmap.md)** — what the Admin Gateway can become once it fronts every MiniMax modality (text, image, video, speech, voice clone, music). Includes picker-slot mapping proposal, per-modality required changes, and Token Plan / Ultra plan context.
5. **[05-sota-game-changers.md](./05-sota-game-changers.md)** — top 3 SOTA / game-changing features (Speculative Skip, MCP Apps Inline UI, C2PA Provenance) with deep dives, plus the full ranked list of 12 patterns.
6. **[06-bugs-and-polish.md](./06-bugs-and-polish.md)** — bug audit of all 12 Python + PowerShell files. 30 issues (5 critical, 9 high, 9 medium, 7 low) with file:line citations and one-line fixes.

## TL;DR

- The Admin Gateway is a ~270-line stdlib-only Python proxy plus PowerShell wiring. It works (live E2E verified against MiniMax) and it never leaks the real key.
- It currently exposes only text. To become a full MiniMax surface it needs 6 new endpoints (OpenAI-compat chat, image gen, video gen async, TTS, voice clone, music gen). Cost estimate on Ultra plan for a single user: ~$175/month total.
- The top 3 SOTA / game-changing features for the gateway are (1) Speculative Skip, (2) MCP Apps Inline UI, (3) C2PA Provenance — see `05-sota-game-changers.md`.
- The 5 critical bugs in `06-bugs-and-polish.md` should ship as a single polish patch (≈1-2 weekends of work).
- Every recommendation is constrained to preserve the patched proxy's "always inject `.env` key and discard client-supplied auth" behavior (`claude-minimax-proxy.py:196-214`).