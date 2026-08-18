# Claude-Desktop MiniMax V2 — Real Gaps Audit

## 1. Environment / orchestrator gaps

| # | Gap | Status | Why it matters | Remediation |
|---|---|---|---|---|
| 1 | `git` CLI | **present** | Hermes `git-*` gates work | None |
| 2 | `gh` CLI | **present** | GitHub fast path works | None |
| 3 | `glab` CLI | **installed** (v1.113.0) | GitLab fast-path / MR gates now available once `GITLAB_TOKEN`/`GLAB_TOKEN` is set | Add `GLAB_TOKEN=<token>` to `claude-minimax-v2\.env` or user env |
| 4 | `HERMES_AGENT_ENABLED` | **1** (in `.env`) | OpenHands / KiloCode autonomous bridge configured | `claude-minimax-v2\.env` sets `HERMES_AGENT_ENABLED=1` and `OPENHANDS_URL=http://127.0.0.1:3333` |
| 5 | `OPENHANDS_URL` | **set** to `http://127.0.0.1:3333` | Hermes Agent has a local OpenHands endpoint | Adjust to `https://openhands.daveai.tech` if using the VPS |
| 6 | Provider registry | **configured** | `HERMES_PROVIDER_REGISTRY` points to `provider_registry.json` | Use `hermes_provider_record_outcome` to populate it |
| 7 | `GITLAB_TOKEN` env var | **missing** in shell (loaded from operator env file) | `glab` / direct CLI won't see token | Source the operator env file or add `GITLAB_TOKEN` to user env |

## 2. Tool / MCP gaps

| # | Gap | Status | Why it matters | Remediation |
|---|---|---|---|---|
| 8 | `Claude_Browser` MCP | only `preview_list` reachable | Cannot actually launch a browser session without a `.claude/launch.json` target | Create `~\.claude\launch.json` with a target URL |
| 9 | `minimax-media` MCP | speech + image verified; music/video untested | Full media suite not proven | Run `minimax_generate_music` / `minimax_generate_video` in a safe test (billed) |

## 3. Quick fixes

Run the script:

```powershell
G:\Github\claude-codex-devin\Fix-RealGaps.ps1
```

This will configure the safe, reversible items (OpenHands env, browser launch target, provider registry placeholder, `.env` for hermes).

## 4. Items that require user action

- Install `glab` from https://gitlab.com/gitlab-org/cli or `winget install glab`.
- Decide whether to enable the Hermes Agent bridge and set the OpenHands endpoint.
- Run paid `minimax-media` music/video tests when ready.
