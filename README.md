# Claude Desktop with MiniMax — safety repair candidate

This project configures the **stock Claude Desktop** application and supplies a
small request-driven MiniMax HTTP adapter. Claude owns its editor sessions,
permissions, terminal and tool execution. The adapter never executes tools.

Use the repaired native-client integration, not Grok's replacement website or
either old watchdog harness. See [the review](docs/SAFETY_REVIEW.md) and
[the repeatable acceptance test](docs/CLAUDE_ACCEPTANCE.md).

## What is included

| Capability | Implementation |
|---|---|
| Windows UI | Windows-MCP 0.8.5: Snapshot, Screenshot, InspectWindow, WindowSetValue, WindowInvoke, WindowClick, WindowType, WindowScroll, WindowMove, WindowShortcut, Wait, WaitFor |
| Project files | Official filesystem MCP 2026.7.10, explicit workspace root, reviewed schema compatibility adapter |
| Browser automation | Playwright MCP 0.0.79, isolated headless Edge profile |
| Library documentation | Context7 4.0.4 |
| Search and image understanding | MiniMax coding-plan MCP 0.0.5 |
| Voice/image/video API tools | Official MiniMax MCP 0.0.19 |
| Windows/Linux coding and VPS | Claude's native terminal, installed Python/Git/WSL/OpenSSH; existing SSH aliases |

SSH does not require another unrestricted shell MCP. The existing `daveai` alias
authenticates as root: use task approval, read-only checks first, and a restricted
deployment account for routine VPS work. No remote account changes are made here.
Unity and other editor-specific bridges are optional project integrations, not
silently started services. Their saved configuration is preserved in backups.

The six MCP processes may stay connected while Claude is open. Tool calls are
task-driven. “No watchdog” does not mean every MCP must be relaunched for every
call; there are no periodic repair loops or automatic restarts in this harness.

## Safety boundaries

- No scheduled health checks, watchdogs, automatic repairs or service recovery.
- No process-name, PID-file, port-owner or unrelated application termination.
- Gateways authenticate locally and bind loopback only. No billed POST retries,
  tool-response cache, placeholder tokens, ambient HTTP proxy or redirects.
- On Windows each gateway has a separate restricted virtual service account,
  256 MiB process memory limit, 20% CPU limit and one-process limit. It cannot
  spawn programs. Only its own log directory is writable by its service SID.
- Requests have explicit concurrency, body, response and time limits. Failure
  produces an error; it does not repair the machine or restart applications.
- The native client asks before shell execution and file changes; managed MCP
  wildcard `ask` rules require per-call approval, including in Code sessions. Windows-MCP
  Process, PowerShell and Registry are absent. UI input is still powerful; never
  use it to bypass approval or operate unrelated applications.

Prefer WindowSetValue and WindowInvoke for supported accessible text fields and
buttons. They resolve a unique named control inside the exact observed window,
without global keystrokes or focus changes. Coordinate input fails when Windows
refuses focus or the point is covered; there is no force-focus workaround.

Filesystem roots constrain that MCP only. They do not sandbox Claude's terminal,
Windows UI, or every third-party media tool. No unrestricted coding assistant
can honestly promise that arbitrary approved commands are harmless.

## Installation and explicit lifecycle (Windows)

Prerequisites: stock third-party Claude Desktop, Python 3.14 on this tested host,
Node.js 22 with npm, PowerShell 7, Edge, and administrator access for service setup.
The Python adapter also has offline CI coverage configured for 3.11 and Linux;
Windows MCP and this installer are Windows-only.

1. Keep source in a trusted local directory. Put `MINIMAX_API_KEY=...` in
   `C:\private\.env`; do not paste a secret into the repository or chat.
2. Run `./Harden-MinimaxEnv.ps1` and `./scripts/Generate-ProxyToken.ps1` explicitly
   in PowerShell 7. Existing local tokens are preserved unless `-Rotate` is used.
3. Run `./scripts/Install-Dependencies.ps1`. Dependencies are pinned, isolated,
   and downloaded only at this explicit step, not when a client connects.
4. Run `./scripts/Install-RequestGateways.ps1 -DownloadWinSW` as administrator.
   On a running installation first close active requests; use `-Activate` only
   for an intentional gateway deployment/restart. WinSW 2.12.0 is SHA256 checked.
5. Run `./Set-ClaudeDesktopGateway.ps1`, then
   `python configure_claude.py --workspace C:\Users\Admin\projects --machine --apply`.
   Substitute your intended, existing projects directory. Configuration changes
   are backed up and never stop applications. Existing model choices are kept.
6. Start the needed gateway explicitly with
   `./scripts/Gateway-Service.ps1 -Gateway Claude -Action Start`.
   Use `-Gateway Codex` only if the Responses adapter is needed.
7. Fully quit and reopen Claude normally. Verify all six servers in the actual
   client, then run the acceptance checks below. Do not force-kill the client.

Machine policy takes precedence over user policy and applies to this host. The
audited MSIX app retained an older user configuration until HKLM was used. This
is why changing a JSON file alone was not sufficient. Profiles with local paths
are intended for this user; multi-user deployment needs per-user provisioning.

Services are **manual start**, so after reboot start the gateway when you need
Claude. There is intentionally no hidden logon task or recovery supervisor.

## Testing

```powershell
./venvs/test/Scripts/python.exe scripts/verify.py
./venvs/test/Scripts/python.exe -m unittest discover -s tests -v
node --test tests/schema-compat.test.mjs
./venvs/test/Scripts/python.exe scripts/Test-ClaudeTools.py --live --ssh-alias daveai
```

The final command runs once, sequentially, in a disposable workspace. `--live`
allows public documentation/search/voice-list and synthetic image-understanding
API calls that can consume quota. Each MCP request has a 120-second deadline;
failures are recorded, not retried automatically.
It prints an evidence JSON path. Omit `--live` for handshake-only checks of those
three remote APIs. It never installs, repairs, changes host keys or kills apps.

Give Claude [docs/CLAUDE_ACCEPTANCE.md](docs/CLAUDE_ACCEPTANCE.md) for a separate
native-client test. A handshake is not proof of working file or Windows tools.
Paid media generation, Cowork VM workflows and every user project remain
separate acceptance tests; they are not marked verified by a voice-list call.

## Scope and release status

This is a repaired **release candidate**, not a zero-bug certification. The
Responses adapter implements stateless text/function/custom-tool round trips,
not every OpenAI server-side feature. Unsupported features fail explicitly.
Token counting is an estimate, not an upstream tokenizer or billing promise.

Windows-MCP 0.8.5's window inventory can omit non-maximizable dialogs. Use a
fresh screenshot for those surfaces; absence from its window list alone is not
proof that a window does not exist. The resizable test fixture avoids that
upstream filtering behavior without altering or granting extra tool authority.

Old audit documents are historical. Do not follow their watchdog, blanket
permission-repair or aggregate-MCP instructions. Retired entry points fail closed.
The source archive is not a self-contained installer and contains no secrets,
Python environments, Node modules, service binaries or user conversations.
