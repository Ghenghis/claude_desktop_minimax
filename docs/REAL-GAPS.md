# Claude-Desktop MiniMax V2 — Real Gaps Audit

## 1. Environment / orchestrator gaps

| # | Gap | Status | Why it matters | Remediation |
|---|---|---|---|---|
| 1 | `git` CLI | **present** | Hermes `git-*` gates work | None |
| 2 | `gh` CLI | **present** | GitHub fast path works | None |
| 3 | `glab` CLI | **installed** (v1.113.0) | GitLab fast-path / MR gates now available once `GLAB_TOKEN` is set in `hermes3d-locks` MCP env | Run `G:\Github\claude-codex-devin\Set-GitLabToken.ps1` with a token in `S:\private\glab_token.txt` or `G:\private\glab_token.txt`, or add `GITLAB_TOKEN` + `GLAB_TOKEN` to `C:\Users\Admin\.codeium\windsurf\mcp_config.json` under `hermes3d-locks` env |
| 4 | `HERMES_AGENT_ENABLED` | **1** (in `hermes3d-locks` MCP config) | OpenHands / KiloCode autonomous bridge now configured in the actual server env | `C:\Users\Admin\.codeium\windsurf\mcp_config.json` sets `HERMES_AGENT_ENABLED=1` and `OPENHANDS_URL=http://127.0.0.1:3333` |
| 5 | `OPENHANDS_URL` | **set** in `hermes3d-locks` MCP config to `http://127.0.0.1:3333` | Hermes Agent has a local OpenHands endpoint | Adjust to `https://openhands.daveai.tech` in `mcp_config.json` if using the VPS; reload the `hermes3d-locks` MCP server |
| 6 | Provider registry | **populated** | `provider_registry.json` created and `HERMES_PROVIDER_REGISTRY` added to `hermes3d-locks` MCP config | `provider_registry.json` is at `C:\Users\Admin\claude-codex-devin\.hermes3d_orchestrator\provider_registry.json`; the Hermes workspace is `C:\Users\Admin\claude-codex-devin` (C: drive, always connected) |
| 7 | `GITLAB_TOKEN`/`GLAB_TOKEN` | **loadable** via `Set-GitLabToken.ps1` or `mcp_config.json` | `glab` / direct CLI needs token; `hermes3d-locks` passes it as env | Run `G:\Github\claude-codex-devin\Set-GitLabToken.ps1` with a token in `S:\private\glab_token.txt` or `G:\private\glab_token.txt`, or add tokens to `mcp_config.json` `hermes3d-locks` env |

## 2. Tool / MCP gaps

| # | Gap | Status | Why it matters | Remediation |
|---|---|---|---|---|
| 8 | `Claude_Browser` MCP | **launch.json created** at `C:\Users\Admin\.claude\launch.json` | `preview_list` should now show targets after the relevant browser MCP reloads | If still empty, reload the `devin/puppeteer` or `claude-browser` MCP server |
| 9 | `minimax-media` MCP | **image/speech/music work; video fails with plan error** | `minimax_generate_video` returns `400` "TokenPlan or Credit does not currently support MiniMax-H3 series models (2013)" | This is an account/plan limit, not a config issue; contact MiniMax or upgrade plan to enable video |

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
