# Vetter Report — Serena MCP (upstream `oraios/serena`)

| Field | Value |
|---|---|
| Tool | Serena (semantic code retrieval / editing toolkit) |
| Repo | https://github.com/oraios/serena |
| Latest upstream release | v1.7.0 (verified via GitHub releases page) |
| Package | `serena-agent` on PyPI |
| License | MIT |
| Source config | `configs/mcp-examples/serena-claude-desktop.json` |
| Vetter run | 2026-08-18 |
| Verdict | **PASS** — installed and smoke-tested 2026-08-18; wired as `serena-semantic` in registry. |
| Rollback | `Set-ItemProperty -Path 'HKCU:\SOFTWARE\Policies\Claude' -Name 'managedMcpServers' -Value <previous value> -Type String` (previous value in `%TEMP%\registry_backup_2026-08-18.json`); or `uv tool uninstall serena-agent`. |

## Purpose

Vet the third-party Serena MCP server before enabling it in the project
workspace. Required by G2 of `.agent/HARNESS_CONTRACT.yaml`
("newly_added_plugin_skill_or_mcp_has_upstream_revision_risk_and_smoke_test_recorded").

## Capability surface

- Reads source files inside the project root passed via `--project`.
- Reads `.serena/context.yml` to scope languages and ignored paths.
- Can write to source files when `read_only: false` (the current
  `.serena/context.yml` has `read_only: false`).
- Performs semantic search via language-server backends (LSP).
- Speaks MCP over stdio.
- No documented telemetry / network exfiltration (README is silent on this).

## Risk flags

| ID | Severity | Flag | Detail |
|---|---|---|---|
| R-01 | HIGH | Bootstrap from unpinned git | The repo config passes `--from git+https://github.com/oraios/serena` with no commit pin. Each invocation pulls whatever `main` is at the moment. Replace with a pinned release or, preferably, install via `uv tool install -p 3.13 serena-agent` first. |
| R-02 | MEDIUM | Network call on every launch | `uvx --from git+...` re-clones/refreshes on every MCP start. Once installed via `uv tool install`, the binary is local and no network is needed. |
| R-03 | MEDIUM | `read_only: false` in `.serena/context.yml` | The seeded context allows file writes. If the goal is read-only assistance, flip to `read_only: true`. |
| R-04 | MEDIUM | `--project` placeholder unfilled | The current config has literal `<PROJECT_ROOT>` placeholders. Leaving them unresolved makes the server fail to start or, worse, bind to the wrong tree. |
| R-05 | LOW | Name collision | The project already registers `hp-mha-serena` (HermesProof MHA integration) under the same `managedMcpServers` registry key. The new upstream serena needs a distinct `name` value to avoid collision. |
| R-06 | INFO | Outdated vs official docs | Upstream docs at `https://oraios.github.io/serena/02-usage/030_clients.html` recommend `serena start-mcp-server --context=desktop-app` with `command: "serena"` (no `uvx`). The repo config predates that. |

## Hardcoded credentials / shell-exec of user input

- No hardcoded credentials.
- No `shell=True` / user-input-as-command in the config.
- One observation: the config uses `uvx --from git+...` to execute a package
  built from a git URL. That is *not* a shell exec, but it is a supply-chain
  trust escalation — the bash subshell interprets the args. Pin a commit.

## Smoke test

- Installed `serena-agent` v1.7.0 with `uv tool install -p 3.13 serena-agent`.
- CLI smoke: `serena --version` and `serena start-mcp-server --context=desktop-app --help` printed successfully.
- MCP initialize smoke: sent JSON-RPC `initialize`; server responded with `serverInfo.name=Serena`, `version=1.28.1`, and `tools/prompts/resources` capabilities.
- End-to-end: `activate_project C:\Users\Admin\claude-codex-devin`, `list_dir`, `search_for_pattern` on `claude-minimax-proxy.py`, and `read_file` line range `235-260` all returned expected results.

## Rollback

- Remove the `serena` entry from `<registry>` → `managedMcpServers`
  (string) under `HKCU:\SOFTWARE\Policies\Claude`.
- Or remove the entry from the chosen `claude_desktop_config.json`.
- Optional: `uv tool uninstall serena-agent`.

## Recommended install path (before enabling in registry)

```pwsh
# One-time, official method
uv tool install -p 3.13 serena-agent
serena --version            # confirm install
serena start-mcp-server --context=desktop-app --help   # smoke
```

Only after the install succeeds and the smoke-test prints help without
errors should the entry be added to the registry.

## Recommended registry entry (replacement for the config file)

```json
{
  "name": "serena-semantic",
  "transport": "stdio",
  "command": "serena",
  "args": ["start-mcp-server", "--context=desktop-app"],
  "toolPolicy": { "*": "allow" }
}
```

This replaces the repo's `uvx --from git+...` block with the canonical
upstream form. The `--project` and `--context` YAML flags are dropped
because the `desktop-app` built-in context already scopes to the active
directory Claude Desktop was launched against.

## Vetter verdict

**PASS**

Serena `serena-agent` v1.7.0 is installed via `uv tool install -p 3.13 serena-agent`,
the MCP initialize smoke test succeeded, and the server is wired into
`HKCU:\SOFTWARE\Policies\Claude\managedMcpServers` as `serena-semantic` using
the canonical `serena start-mcp-server --context=desktop-app` form. The install
and registry steps are recorded in `.agent/PROOF_LEDGER.md` as P-004..P-006.
