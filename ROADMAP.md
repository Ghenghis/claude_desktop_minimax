# Consolidated ROADMAP: Claude Desktop / Codex ↔ MiniMax Gateway

## Project Goal

Enable both **Claude Desktop** and **ChatGPT Codex** to call MiniMax text, vision, speech, and image/video models through a single local gateway (`claude-minimax-proxy.py`) running on `127.0.0.1:48217`, and document the end-to-end integration with blueprints and automation.

---

## Phase 0 — Claude Desktop 401 Fix (DONE)

- [x] Audit `docs/admin-gateway-audit`, `architecture.md`, `threat-model.md`, and existing `ROADMAP/*` artifacts.
- [x] Patch `claude-minimax-proxy.py` to accept the proxy token via `X-Api-Key` or `Authorization: Bearer` in addition to `X-Proxy-Token`.
- [x] Generate `G:\private\.proxy-token` (256-bit random hex) and apply an owner-only ACL.
- [x] Configure `HKCU:\SOFTWARE\Policies\Claude` with the gateway base URL, API key, and `x-api-key` auth scheme.
- [x] Verify end-to-end: `POST /anthropic/v1/messages` returns `200` from MiniMax `MiniMax-M2.1`.

**Artifacts:**

- `claude-minimax-proxy.py` (patched auth, lines 430-449)
- `scripts/Repair-MinimaxGateway.ps1` (idempotent token/ACL/registry/proxy repair + verify)
- Registry values under `HKCU:\SOFTWARE\Policies\Claude`

---

## Phase 1 — Codex Configuration (DONE)

- [x] Add `model_provider = "minimax_gateway"` and `[model_providers.minimax_gateway]` to `C:\Users\Admin\.codex\config.toml`.
- [x] Use `wire_api = "responses"` pointing at `http://127.0.0.1:48217/v1`.
- [x] Use `auth.command` so Codex reads the proxy token from `G:\private\.proxy-token` on demand.

**Artifacts:**

- Updated `C:\Users\Admin\.codex\config.toml`

---

## Phase 2 — Documentation (IN PROGRESS)

- [x] Write `docs/E2E-Blueprint.md` with detailed Mermaid diagrams for both Claude Desktop and Codex request flows.
- [x] Write this `ROADMAP.md` tying research, fixes, and next steps together.
- [ ] (Optional) Add short `README` cross-links in `Testing-Claude-Minimax-Mcp` for discoverability.

---

## Phase 3 — Proxy Wire-Protocol Expansion (DONE)

- [x] Add `/v1/responses` support to `claude-minimax-proxy.py` so Codex can switch to `wire_api = "responses"` without 404.
- [ ] Map OpenAI Responses API fields (tools, reasoning, output format) to MiniMax chat or Anthropic messages.
- [ ] Preserve streaming, tool-call id, and stop-reason fidelity.

**Acceptance criteria:**

```bash
codex --model MiniMax-M3 --provider minimax_gateway "explain this repo"
# returns a streamed response with no 404 and no model errors
```

---

## Phase 4 — Multimodal Pipelines (NEXT)

- [ ] Expose dedicated `model_providers` profiles in `~/.codex/config.toml` for:
  - `image-01` image generation
  - `speech-02-hd` / `speech-02-turbo` TTS
  - `I2V-01` / `T2V-01` video generation
  - `MiniMax-M3` vision via the `/v1/chat/completions` multimodal endpoint
- [ ] Add `mcp_servers.minimax-media` or equivalent to surface media tools in Codex.
- [ ] Document per-model payload shapes and upload flows.

---

## Phase 5 — Hardening & Governance (NEXT)

- [ ] Integrate `hp-mha-serena` runtime registration for the proxy so it is governed, hashed, and auto-restarting.
- [ ] Add structured logging/telemetry to the proxy (request id, model, tokens, latency).
- [ ] Implement token hot-reload without restart (`MINIMAX_PROXY_TOKEN_DISABLED` already supported for dev).
- [ ] Add unit/regression tests for token validation, model rewriting, and upstream failover.

---

## Phase 6 — GitOps & Release (DONE)

- [x] Organize and commit Phase 0-2 changes to `Ghenghis/claude_desktop_minimax`.
- [x] Push documentation and integration notes to `claude-codex-devin/docs/diagrams` and `portable/`.
- [x] Build `G:\Github\claude-minimax-v2-portable.zip`.
- [x] Tag `v2.0.0` release.
- [x] Fix `minimax-media` MCP `transport closed` by registering `python.exe` + `server.py` directly in `managedMcpServers`.

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| `wire_api = "responses"` for Codex | Codex now requires the OpenAI Responses API. The proxy translates `POST /v1/responses` to `POST /v1/chat/completions` and back. |
| `Authorization: Bearer` for proxy token | Both Claude Desktop and Codex can emit a bearer token; the proxy accepts all three header forms. |
| `auth.command` reads `.proxy-token` | Avoids persisting the token inside `config.toml` and refreshes on each use. |
| Forward slashes in `G:/private/.proxy-token` | Eliminates TOML and PowerShell backslash escaping issues in `config.toml`. |

---

## Quick-Start for New Environments

1. Run `scripts/Repair-MinimaxGateway.ps1` to create the token, set registry, and start the proxy.
2. Open Claude Desktop and verify the third-party gateway option is selected.
3. In Codex, run `codex --model MiniMax-M3 --provider minimax_gateway "hello"`.
4. See `docs/E2E-Blueprint.md` for request flows and troubleshooting.
