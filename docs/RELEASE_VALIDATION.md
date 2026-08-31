# Release validation — 2026-08-30

Decision: keep stock Claude Desktop and repair the request-driven MiniMax
integration. Do not ship Grok's replacement website or either watchdog harness.
This is a tested release candidate for the workflows below, not a guarantee of
zero bugs or complete proprietary Claude feature parity.

## Audited installation

- Stock Claude Desktop 1.40609.0.0, Code SDK 2.1.247, Windows, Python 3.14.
- Active source: `C:\Users\Admin\claude-codex-devin`.
- Deployed gateway code: `C:\ProgramData\ClaudeMiniMax`.
- Six direct pinned MCPs: Windows-MCP, project-files, Playwright, Context7,
  MiniMax coding-plan, and official MiniMax media. No aggregate supervisor.
- Project-files root: `C:\Users\Admin\projects`. Native Code file/terminal
  tools operate in the selected project; this MCP root is not a shell sandbox.
- Gateways are manual-start restricted services, with no recovery actions.
  Each gateway process has a 256 MiB memory limit, 20% CPU limit, and child
  creation denied. Gateway executables cannot run tools or control applications.

## Observed verification

| Check | Result and scope |
|---|---|
| Offline contracts | 51 Python tests pass on Windows. Linux runs the same suite with two Windows Job Object tests skipped. |
| Schema adapter | Three Node tests pass; draft-07 conversion preserves reviewed constraints and rejects unsupported dialect features. |
| CI | Windows and Ubuntu, Python 3.11 and 3.14, all pass. See [the runtime-change run](https://github.com/Ghenghis/claude_desktop_minimax/actions/runs/33344840242). |
| Native coding | Claude created a small Python module and three meaningful unit tests; tests exited 0. |
| Native files | Official filesystem MCP wrote/read the exact marker after correcting the native client's schema incompatibility. Direct tests deny outside-root reads. |
| Native Windows | Snapshot located the disposable fixture; InspectWindow identified its controls; WindowSetValue wrote/read back the marker; WindowInvoke operated Verify; final static-label inspection returned CLAUDE_WINDOWS_TEST_PASSED. |
| Windows refusal behavior | A real WindowType call was refused when Windows denied foreground focus. No input was sent. Offline checks also reject covered points, mismatched windows, ambiguous controls, password fields, and incomplete searches. |
| Native browser | Isolated Playwright opened Example Domain, verified its heading, and closed its own browser. A direct local-fixture interaction also passes. |
| Documentation and search | Native Context7 library resolution and MiniMax public web search pass. |
| Image understanding | Direct MiniMax coding-plan call correctly identified a generated solid-red image. No user image uploaded. |
| Media API | Native and direct official MiniMax voice-catalogue calls pass; generation, voice cloning and paid video jobs were not run. |
| Native VPS | Existing OpenSSH alias daveai passed strict host verification and the read-only OS/account query; Linux/root, exit 0. No VPS writes. |
| Native Linux | WSL Ubuntu computed 2+3 as 5 and fetched example.com over HTTPS with status 200, both exit 0. |
| Deployed model routes | Claude M3, M2.7, highspeed, and stateless Responses calls completed successfully after deployment. |
| Short soak | 325 requests; latest local run retained 73,803 Python bytes, threads 3 to 3. This is not a long-duration memory-leak certification. |
| Dependency review | No known vulnerabilities reported by npm audit or pip-audit for the four runtime locks and acceptance-test lock at review time. No claim about undiscovered vulnerabilities. |
| Source hygiene | Python verification, PowerShell manifest parsing, schema tests and credential scan pass. Private logs/backups/environments excluded from the source allowlist. |

## Failures found and corrected

- The packaged app retained stale effective configuration. The complete managed
  machine profile was applied with backups and verified in the actual client.
- Filesystem output schemas used a dialect the client rejected. A narrow
  compatibility adapter was added instead of removing output validation.
- Upstream Windows inspection omitted some windows/static labels. Exact-window
  inspection now includes visible static labels without scanning other windows.
  `Snapshot(use_ui_tree=false)` skips window enumeration; the input-test prompt
  now explicitly uses `true` when it needs to find the fixture.
- Global input could not safely cross focus changes. Window-scoped guards fail
  closed; supported fields/buttons use accessibility patterns without global
  keystrokes, forced foreground changes, or attached application input queues.
- Windows CI caught an overloaded socket closing before the client read 503.
  The error path now half-closes and drains at most 64 KiB for at most 50 ms,
  without an extra worker or retry. Repeated GET/POST rejection tests pass.
- One earlier image-understanding run timed out at the test's 40-second limit.
  The test now has an explicit 120-second per-request limit and records failure
  types; subsequent complete runs pass. It never retries automatically.

## Containment and remaining limits

Six host tasks were backed up and disabled: the two MiniMax watchdog tasks, two
health tasks, MiniMax environment maintenance, and VSCode-Health-Audit-Hourly.
The VSCode task launched PowerShell without a hidden window near the reported
popup. Task history was disabled, so every earlier popup cannot be attributed.
The old connected daves-tools supervisor was disconnected and locally quarantined.
Unrelated applications and Codex-owned tool processes were not mass-terminated.

Services deliberately do not start after reboot. Start the needed gateway with
`scripts/Gateway-Service.ps1 -Gateway Claude -Action Start`, then open Claude.
The native client requests per-call approval; automatic approval is not needed.

The SSH alias currently uses root. Use a restricted deployment account for routine
unattended work; this task did not create accounts or change remote permissions.
WSL reports a NAT-to-VirtioProxy fallback on this host, but the tested Linux HTTPS
workflow succeeds. No machine-wide networking repair was attempted.

Windows coordinate input can require manual focus; it intentionally refuses
unsafe conditions. Accessibility patterns require application support. Arbitrary
approved shell/UI actions still carry risk. This is not a universal OS sandbox.
UI provider calls, network availability, upstream APIs and stock-client defects
remain external dependencies. No always-running health checker was added.

Cowork VM workflows, paid media generation, optional Unity/IDA/database bridges,
every real coding project, fresh-machine installation, and multi-day uptime have
not been certified. Test those against their intended project and target before
claiming support. The source ZIP excludes dependencies and is not an installer.

GitHub publication preserves its existing history on a separate safety branch.
GitLab's saved token was expired; it was not rotated, printed or bypassed.
