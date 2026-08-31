# Security and operational limits

Report security defects privately to the repository owner. Do not include API
keys, registry exports, user conversations or private project files in reports.

The HTTP adapters have no tool execution authority. They use authenticated
loopback listeners, fixed upstream destinations, bounded request sizes,
concurrency and duration, and do not retry billed requests. On Windows deployment
adds separate non-administrator service identities, restricted write access and
job-object CPU/memory/child-process limits. The limits are fail-closed at startup.

The client and MCP tools are a different trust boundary. Native approvals must
remain enabled. An MCP that reads files, a browser with network access, a shell,
or Windows clicking and typing can expose or change data when used. Folder
allowlists are not shell sandboxes. UI commands must never be used to bypass
security prompts. Root SSH is not a safe default for unattended deployments.

No service, timer, watchdog or health script may stop unrelated processes,
restart an application, change its permissions, or “repair” the whole machine.
Owned service shutdown is an explicit maintenance operation only and interrupts
that service's in-flight requests. No automatic recovery is configured.

Dependencies are pinned in separate environments. A clean vulnerability scan
does not prove absence of malicious behavior or undiscovered vulnerabilities.
Python pins are version locks, not wheel hashes; WinSW and Node integrity hashes
are verified. Review dependency upgrades before applying them.

Secrets remain outside the repository. The gateway receives only its MiniMax
key and local token, not the user's entire secret file. Backups containing
configuration secrets stay local and must not be published. Do not use ACL deny
rules against Everyone: they can also deny the administrator access.

Stock Claude and upstream MCPs are not rewritten here. Browser/CDP, media API,
WSL and editor-specific capabilities require their own task-scoped testing.
There is no claim of complete Claude feature parity or absence of all leaks.
