# PROJECT STATE

## Goal
Integrate the DAVE-AI Agent Harness for Reverse Engineering, Android, and Windows into the Claude Desktop workspace, then polish the setup so it is self-documenting and reproducible.

## Acceptance Criteria
- [x] DAVE-AI contracts copied from `G:\` to `C:\Users\Admin\claude-codex-devin\contracts\` with clear names.
- [x] Project initialized and 12 DAVE-AI skills installed into `.claude\skills\`.
- [x] Preflight script runs without `Get-Command` stderr cancellation and emits `.agent\DAVEAI-preflight.json`.
- [x] Serena MCP server vetted, installed, and wired into `HKCU:\SOFTWARE\Policies\Claude\managedMcpServers` as `serena-semantic`.
- [x] `README-CLAUDE-INTEGRATION.md`, `VETTER-serena-2026-08-18.md`, and `PROOF_LEDGER.md` reflect the live, smoke-tested state.
- [ ] Claude Desktop restarted and `serena-semantic` loaded in the MCP server list.

## Authorization / Scope
User-authorized scope for this workspace only. No destructive action against the G:\ source harness or the live DaveAI VPS.

## Constraints
- Work only inside `C:\Users\Admin\claude-codex-devin`.
- Follow the `DAVEAI_HARNESS_CONTRACT.yaml` fail-closed / proof-record rules.
- No hardcoded credentials or API tokens in tracked files.

## Active Profile
CORE

## Current State
- DAVE-AI skills and contracts are in place.
- `serena-agent` v1.7.0 is installed via `uv` and the registry entry uses the canonical `serena start-mcp-server --context=desktop-app` form.
- Documentation, vetter report, and proof ledger have been updated to match the actual smoke-test results.

## Last Known Good
- 2026-08-18: preflight-safe.ps1 completes, DAVE-AI skills load, serena MCP initialize responds.

## Current Failure / Evidence
None.

## Completed Gates
- P-002: 12 DAVE-AI skills present.
- P-003: Serena G2 vetter now PASS.
- P-004: `serena-agent` installed.
- P-005: `serena start-mcp-server` MCP initialize PASS.
- P-006: `managedMcpServers` registry updated.

## Next Exact Action
Restart Claude Desktop and verify `serena-semantic` appears and the DAVE-AI skills are active in the project workspace.

## Rollback / Backup
- Previous `managedMcpServers` registry value backed up at `%TEMP%\registry_backup_2026-08-18.json`.
- `uv tool uninstall serena-agent` removes the package if needed.

## Open Blockers
None.
