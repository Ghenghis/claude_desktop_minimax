# Claude-Desktop MiniMax V2 — Real Gaps Audit

## 1. Environment / orchestrator gaps

| # | Gap | Status | Why it matters | Remediation |
|---|---|---|---|---|
| 1 | `git` CLI | **present** | Hermes `git-*` gates work | None |
| 2 | `gh` CLI | **present** | GitHub fast path works | None |
| 3 | `glab` CLI | **installed** (v1.113.0) | GitLab fast-path / MR gates now available once `GITLAB_TOKEN`/`GLAB_TOKEN` is set | Add `GLAB_TOKEN=<token>` to `claude-minimax-v2\.env` or user env |
| 4 | `HERMES_AGENT_ENABLED` | **1** (in `.env`) | OpenHands / KiloCode autonomous bridge configured | `claude-minimax-v2\.env` sets `HERMES_AGENT_ENABLED=1` and `OPENHANDS_URL=http://127.0.0.1:3333` |
| 5 | `OPENHANDS_URL` | **set** to `http://127.0.0.1:3333` | Hermes Agent has a local OpenHands endpoint | Adjust to `https://openhands.daveai.tech` if using the VPS |
| 6 | Provider registry | **populated** | `hermes_provider_rank` now returns rankings for 6 providers after recording baseline outcomes | `hermes_provider_record_outcome` used for minimax/deepseek/deepinfra/siliconflow/lm-studio/ollama |
| 7 | `GITLAB_TOKEN`/`GLAB_TOKEN` | **loadable** via `Set-GitLabToken.ps1` | `glab` / direct CLI needs token in shell env | Run `G:\Github\claude-codex-devin\Set-GitLabToken.ps1` with a token in `S:\private\glab_token.txt` or `G:\private\glab_token.txt` |

## 2. Tool / MCP gaps

| # | Gap | Status | Why it matters | Remediation |
|---|---|---|---|---|
| 8 | `Claude_Browser` MCP | only `preview_list` reachable | Cannot actually launch a browser session without a `.claude/launch.json` target | Create `~\.claude\launch.json` with a target URL |
| 9 | `minimax-media` MCP | image/speech/music work; **video and complex jobs still untested** | Video endpoint not proven | Run `minimax_generate_video` in a safe test (billed) or accept documented limitation |

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
