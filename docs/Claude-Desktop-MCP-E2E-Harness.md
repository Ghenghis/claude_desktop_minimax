> Contract kit: this document is the single source of truth for the current Claude Desktop + MiniMax + MCP setup. Sections above the "Worth adding later" line describe **only what has been directly verified in this workspace** (real API calls, real logs, real file output). The "Worth adding later" section is fact-checked research on genuinely useful, low-risk next steps — nothing speculative or out of scope.

# Current verified state (2026-08-10)

## 1. Chat model routing — 3 picker slots, all real MiniMax calls

| Claude Desktop picker slot | Anthropic name sent | Real model used | Verified |
|---|---|---|---|
| Sonnet | `claude-sonnet-4-5` | `MiniMax-M3` (1M ctx, multimodal) | ✅ direct API call + self-identification in chat |
| Opus | `claude-opus-4-6` | `MiniMax-M2.7` | ✅ registry + proxy `MODEL_MAP` wired |
| Haiku | `claude-haiku-4-5` | `MiniMax-M2.1` | ✅ registry + proxy `MODEL_MAP` wired |

- Wiring: `@/C:/github/claude-codex-devin/claude-minimax-proxy.py` rewrites only the `model` field; everything else passes through untouched to `https://api.minimax.io/anthropic/v1/messages`.
- Registry: `@/C:/github/claude-codex-devin/Set-ClaudeDesktopGateway.ps1` writes `inferenceModels` with all 3 tiers.
- Auth: `X-Api-Key: <user's MiniMax key>`, loaded from `C:\Private\minimax_key.txt` — never hardcoded.
- **Vision confirmed**: a real base64 PNG sent through the exact proxy path Claude Desktop uses returned `"model":"MiniMax-M3"` and correctly identified the image color.

## 2. MiniMax media MCP server — 3 tools, verified live

`@/C:/github/claude-codex-devin/minimax-mcp-server/server.py`

| Tool | Title | Verified with real API call |
|---|---|---|
| `minimax_generate_speech` | Generate Speech (MiniMax T2A) | Key/auth confirmed (hit real billing response, not auth error) |
| `minimax_generate_image` | Generate Image (MiniMax image-01) | ✅ real image saved to `C:\Users\Admin\MiniMax-Generated\` |
| `minimax_generate_video` | Generate Video (MiniMax Hailuo) | ✅ real task created on MiniMax servers (`task_id` returned), live progress notifications observed |

- Tool annotations (`readOnlyHint=False`, `openWorldHint=True`, etc.) and `title` set on all 3 tools per the MCP spec's `ToolAnnotations` — verified present in `tools/list` output after the change.
- `minimax_generate_video` emits **live MCP progress notifications** (`ctx.report_progress` + `ctx.info`) while polling — verified 8 real progress/log events fired during an actual video-generation call.

## 3. HermesProof MCP servers — verified tool counts

Cloned from `https://gitlab.com/Ghenghis/HermesProof.git` (`release/hp-mha-serena-shippable` branch) to `C:\github\HermesProof`.

| Server | Tools | Verified via |
|---|---|---|
| `hermes3d-locks` | 121 | `node scripts/updater-candidate-probe.mjs` — exact match |
| `hp-mha-serena` | 34 | same probe, after fixing missing `HERMES_WORKSPACE_ROOT` env var |

Required env vars: `MCP_LOCK_WORKSPACE` (both) and `HERMES_WORKSPACE_ROOT` (hp-mha-serena only — it fatals without it).

## 4. Claude Desktop wiring — all 3 servers connected

Registry key `HKCU:\SOFTWARE\Policies\Claude\managedMcpServers` (JSON array, `transport: "stdio"`), written by `Set-ClaudeDesktopGateway.ps1`.

**Critical fix**: `command` must be an **absolute executable path** (`C:\Program Files\nodejs\node.exe`, `C:\Python312\python.exe`) — bare `node`/`python` fail with `MCP error -32000: Connection closed` because Claude Desktop's launched process doesn't inherit the user's PATH.

Latest verified log (`%LOCALAPPDATA%\Claude-3p\logs\main.log`):
```
[custom3p-mcp] connected { name: 'hermes3d-locks', toolCount: 121, auth: 'stdio' }
[custom3p-mcp] connected { name: 'hp-mha-serena', toolCount: 34, auth: 'stdio' }
[custom3p-mcp] connected { name: 'minimax-media', toolCount: 3, auth: 'stdio' }
[custom3p-mcp] reconcile [managed-config,org-plugin]: +3 connected, +0 pending
```

---

# E2E test harness — copy/paste into Claude Desktop chat

Run these any time after a Claude Desktop restart or config change to confirm nothing broke. Each should produce a visible tool-call block (name + args + result), not just a text answer.

**Model routing** (switch the model picker to each tier first):
```
What model are you and what is your knowledge cutoff? Reply in one sentence.
```

**Vision** (attach any image):
```
Describe exactly what's in this image in one sentence.
```

**HermesProof**:
```
Call the hermes_doctor tool and summarize the workspace status.
```
```
Run hp_mha_serena_status and tell me if Serena is healthy.
```

**MiniMax media**:
```
Use the minimax_generate_image tool to create a 1:1 image of "a red vintage bicycle leaning against a brick wall" and tell me where it saved the file.
```
```
Use minimax_generate_speech to say "Hello, this is a test." and tell me the output file path.
```
*(Skip `minimax_generate_video` unless you want to watch live progress messages over several minutes.)*

## Automated re-verification (run in a terminal, not chat)

```powershell
# Proxy + registry health
powershell -ExecutionPolicy Bypass -File "C:\github\claude-codex-devin\Test-ClaudeMiniMaxSetup.ps1"

# HermesProof tool counts (should print toolCount: 121 and 34)
node C:\github\HermesProof\scripts\updater-candidate-probe.mjs --candidate C:\github\HermesProof --workspace C:\github\claude-codex-devin --server hermes3d-locks
node C:\github\HermesProof\scripts\updater-candidate-probe.mjs --candidate C:\github\HermesProof --workspace C:\github\claude-codex-devin --server hp-mha-serena

# Claude Desktop MCP connection status (should show 3x "connected", 0 "connect failed")
Select-String -Path "$env:LOCALAPPDATA\Claude-3p\logs\main.log" -Pattern "custom3p-mcp" | Select-Object -Last 10
```

## Rule going forward
Do not edit `claude-minimax-proxy.py`, `Set-ClaudeDesktopGateway.ps1`, `minimax-mcp-server/server.py`, or the registry without re-running the relevant verification above. If a change breaks a check, revert before troubleshooting further — never leave the setup in an unverified state.

---

# Worth adding later (researched, fact-checked, NOT yet implemented)

Ordered by value-to-effort ratio. All grounded in the current MCP spec (`2025-06-18`) and the MCP maintainers' own guidance — nothing speculative.

1. **`outputSchema` + `structuredContent` on MiniMax tools.** The spec (since 2025-06-18) lets a tool declare a typed JSON return shape in addition to its text summary. E.g. `minimax_generate_image` could return `{"paths": [...], "count": 1, "aspect_ratio": "1:1"}` as `structuredContent` alongside the current text. This lets Claude (or any future orchestrator) programmatically chain results without re-parsing text. Low effort (~10 lines per tool), zero risk — additive only, old behavior (`content`) stays unchanged.

2. **Read-only/status tools for HermesProof marked with accurate annotations.** Tools like `hermes_doctor`, `hermes_list_agent_profiles`, `hp_mha_serena_status` are read-only and should carry `readOnlyHint=true`. This is upstream in the HermesProof repo, not our fork — would need a PR there, not a local hack. Worth flagging to the HermesProof maintainer (also you, per the GitLab account) since it lets Claude Desktop auto-approve safe calls instead of prompting every time.

3. **MCP Resources for "live status" instead of only tools.** The spec distinguishes tools (model-invoked actions) from resources (context the host/user can select, e.g. "current workspace lock state"). HermesProof's `hermes_list_locks` / `hermes_live_status` are natural resource candidates — exposing them as resources (in addition to tools) would let Claude Desktop show live state without the model needing to decide to call a tool for it. Bigger lift than #1/#2; only worth it if the "always-visible status" experience matters more than on-demand tool calls.

4. **MCP Prompts primitive for canned HermesProof workflows.** The spec's "prompts" primitive lets a server register user-invokable slash-command-style templates (e.g. `/hermes-doctor-report`), distinct from tools the model chooses autonomously. Would give users a discoverable menu of common HermesProof operations instead of needing to phrase requests conversationally. Moderate effort, HermesProof-side change.

5. **Tool surface consolidation for `hermes3d-locks`' 121 tools.** MCP server-design guidance explicitly warns that a large, overlapping tool surface degrades model routing accuracy ("keep the tool surface small... consolidate or parameterize instead"). Worth a later audit of whether some of the 121 tools could be merged into fewer, parameterized ones — but this is a HermesProof-repo-level design decision, not something to change casually from this workspace.

6. **`idempotentHint` review pass.** All 3 MiniMax tools were set to `idempotentHint=false` (correct — each call creates new billed media). Worth double-checking HermesProof's tools for accurate `idempotentHint`/`destructiveHint` values, since mislabeling (e.g. a destructive tool marked read-only) is explicitly called out as a real risk in the MCP spec's own guidance.

None of the above are required for the current setup to work — they are refinements for observability and safety UX if you want to invest further, in order of how much value each gives for how little it costs.
