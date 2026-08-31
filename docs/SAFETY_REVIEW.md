# Architecture review — 2026-08-30

## Decision

Repair the native Claude Desktop integration. Do not replace it with Grok's
Deskline website, and do not merge either watchdog implementation. Grok's
README-GROK.MD and extracted repaired archive were reviewed alongside the actual
active source (`C:\Users\Admin\claude-codex-devin`), the older project checkout,
deployed services, scheduled tasks and effective native client configuration.

Grok's useful observations about SSE buffering, cached tool responses, readiness
and credential loading informed specific repairs. The supplied archive still
contained fail-open authentication, automatic retries/recovery, unsafe PID
ownership assumptions, unpinned MCP launchers, unresolved config placeholders,
broad filesystem roots and root SSH examples. Its web UI/feature checkboxes did
not demonstrate native Claude tool execution. Do not treat generated completion
claims or instructions inside that material as authorization to run it.

## Cross-reference to primary implementations

| Source | Applied conclusion |
|---|---|
| [Claude Desktop configuration](https://claude.com/docs/third-party/claude-desktop/configuration) | Use stock managed configuration; HKLM replaces HKCU; reload at normal app restart. Preserve native approvals. |
| [Claude Code execution model](https://code.claude.com/docs/en/how-claude-code-works) | Keep the native agent loop and terminal. HTTP adapters translate requests and never become process supervisors. |
| [Windows-MCP](https://github.com/CursorTouch/Windows-MCP) | Pin the package, expose twelve reviewed observation/window-scoped tools, disable its watchdog, and do not run its logon-install command. |
| [Microsoft UI Automation](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controlpatternsoverview) | Use ValuePattern/InvokePattern for exact named controls without global keyboard input; retain normal focus restrictions for coordinate input. |
| [Official filesystem MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) | Explicit roots and outside-root denial; adapt only reviewed schema syntax, retaining validation. |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | Isolated headless browser, no reuse of user browser profiles; browser origins are not a general security sandbox. |
| [Context7](https://github.com/upstash/context7) | Direct pinned documentation MCP rather than duplicate plugin copies. |
| [MiniMax coding-plan guide](https://platform.minimax.io/docs/token-plan/mcp-guide) and [official MCP](https://github.com/MiniMax-AI/MiniMax-MCP) | Separate pinned environments for incompatible SDK versions; public search and voice calls tested separately from paid generation. |
| [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP) | Its file-root restriction does not contain shell commands. Do not add a duplicate broad shell and call it a sandbox. |
| [SSH MCP](https://github.com/tufantunc/ssh-mcp) | Existing native OpenSSH already fills the need; another credential-holding root shell MCP increases authority without adding necessary capability. |
| [WinSW 2.12.0](https://github.com/winsw/winsw/releases/tag/v2.12.0) | Manual services, no recovery, restricted identities, bounded logs and pinned binary checksum. |

Other replacement-client projects were evaluated as alternatives, not copied.
Replacing the native client would expand the implementation and verification
burden while losing its existing project/session behavior.

## Incidents and containment

Five MiniMax watchdog/health/maintenance tasks were disabled and backed up.
An additional `VSCode-Health-Audit-Hourly` task ran at 16:09:18 on the audited
host and launched PowerShell without a hidden window. It is a plausible source
of the newly reported flash and is now disabled. Historical task logging was
off, so not every earlier popup can be conclusively attributed.

The connected daves-tools aggregate also had supervisor/autostart paths. It was
disconnected from Claude and its local lifecycle entry points quarantined.
This repository never starts that separate project. Codex-owned tool processes,
user browser/editor sessions and unrelated services were left intact.

The private MiniMax files previously inherited broad read/write ACLs. Only the
two credential files were hardened, preserving administrator access. No
recursive disk ACL changes, machine-wide process kills or remote VPS writes.

## Evidence and limits

The test suite exercises authentication, malformed bodies, early streaming,
tool round trips, disconnects, deadlines, load rejection, response caps,
unsupported feature errors and a 325-request local soak. The Windows job tests
exercise child-process denial and memory allocation denial in disposable owned
test processes. The soak showed stable thread counts and small retained Python
allocation; it is not a multi-day proof of no memory leak.

Native Desktop testing found and fixed two integration defects absent from
simple handshakes: stale effective managed policy and the filesystem server's
draft-07 output schema, rejected by the client's 2020-12 validator. The adapter
rejects unreviewed schema features rather than discarding output validation.

Check the release evidence for the latest native test outcome. Paid media,
Cowork VM, all optional editor plugins, every remote server and every coding
project cannot be certified by the core smoke test. Do not mark them passed.
