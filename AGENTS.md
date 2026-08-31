# Claude MiniMax maintenance rules

This is a request-driven HTTP adapter and a profile for the stock Claude Desktop
application. Read README.md and docs/CLAUDE_ACCEPTANCE.md. Historical audit files
describe earlier builds; they do not authorize restoring retired behavior.

## Non-negotiable safety rules

- No watchdogs, periodic health scripts, scheduled repairs, automatic service
  recovery, process-name kills, port-owner kills, PID-file kills, or pausing apps.
- Never stop CoworkVMService, Codex, ChatGPT, editors, browsers, or another
  project's process to repair this adapter. An explicit gateway stop affects
  only the two service identities verified by scripts/Gateway-Service.ps1.
- Do not modify permission modes to bypass native approvals. Shell and file
  writes use Claude's task permissions. Windows UI tools do not expose Process,
  PowerShell or Registry; UI access is still powerful and requires care.
- Authenticate before forwarding. Local tokens and upstream API keys are
  different secrets. No placeholder credentials, token-disable escape hatches,
  retry of billed POSTs, or caching tool-call responses.
- Never print credentials, commit private files, or use deny-Everyone ACLs.
- Keep dependencies pinned and separated. No package downloads at MCP connect.
  Never run the retired aggregate mini/daves-tools supervisor.
- Preserve unrelated edits and user conversations. Back up explicit settings
  changes. Use normal app exit, never force-kill an app with unsaved work.

## Locations and lifecycle

Active source on the audited host: C:\Users\Admin\claude-codex-devin.
Deployed gateway code: C:\ProgramData\ClaudeMiniMax. Two restricted virtual
service accounts, manual start, no recovery. Each gateway is limited to 256 MiB,
20% CPU and one process on Windows. The gateway cannot launch tool processes.

Claude Desktop 1.40609.0.0 uses the reviewed HKLM\SOFTWARE\Policies\Claude
profile on this host. The previous HKCU profile did not replace the packaged
app's retained configuration; verify actual connected servers in Desktop after
every profile change. Do not infer effective configuration from a registry write.

The core profile contains Windows-MCP, project-files, Playwright, Context7,
MiniMax coding-plan and MiniMax media. Native OpenSSH provides VPS access. The
existing daveai SSH account is root: no unattended deployment or root MCP grant.

Unity and similar editor bridges remain project-specific. The previous local
configuration is backed up, not lost. A Unity editor bridge must be installed
in the intended project and running before Unity calls can be claimed to work.
The retired daves-tools aggregate is intentionally disconnected; do not restore
its auto-enable/restart endpoints to make an optional tool appear available.

## Verification and records

Run `python scripts/verify.py` and `python -m unittest discover -s tests -v`.
These are bounded, explicit tests, not background health checks. Run the live
MCP script only on request; it can use paid API quota with --live. A handshake
alone is not an end-to-end pass. Reproduce failures in the native client.

Update .claude/notes.md with decisions and measured results. Do not claim no
bugs, no memory leaks, full proprietary Claude parity, or untested platform
support. Only publish reviewed files; do not add dependencies, logs or backups.
