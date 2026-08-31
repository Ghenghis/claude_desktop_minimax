# Project Notebook — Admin Gateway

This is the persistent scratchpad (Reflexion-style episodic memory). Read it at the
start of every session; append to it whenever you learn something the next agent
needs to know.

## Format

```
## YYYY-MM-DD — <one-line summary>

**Tried**: <what was attempted>
**Result**: <succeeded / failed / partial>
**Why**: <root cause or rationale>
**Lesson**: <what to do (or not do) next time>
**Status**: <open / resolved / wontfix>
```

---

## Project state snapshot

- Last verification: _fill in date after next successful verifier run_
- Open blockers: _none_ (or list them)
- Current focus: shipping weekend MVP autonomous-agent harness

---

<!-- Append new entries below. Do not edit or delete above this line. -->

## 2026-08-18 — DAVE-AI skills confirmed loaded; serena vetter CONDITIONAL PASS

**Tried**: Verified all 12 `daveai-*` skills under `.claude/skills/` carry a valid `SKILL.md`. Then vetted the *upstream* `oraios/serena` per `daveai-skill-vetter` (G2 gate).
**Result**: 12/12 active skills load. Serena vetter returned CONDITIONAL PASS.
**Why**: Serena is not yet installed (`uv tool list` shows no `serena-agent`); `uvx` is present (v0.12.5). The repo config `configs/mcp-examples/serena-claude-desktop.json` uses `uvx --from git+https://github.com/oraios/serena` with no commit pin and a literal `<PROJECT_ROOT>` placeholder — outdated vs upstream docs which recommend `uv tool install -p 3.13 serena-agent` and `serena start-mcp-server --context=desktop-app`.
**Lesson**: Don't add the registry entry until `uv tool install -p 3.13 serena-agent` completes and `serena start-mcp-server --context=desktop-app --help` prints. The project already has `hp-mha-serena` (HermesProof MHA) wired via `HKCU:\SOFTWARE\Policies\Claude\managedMcpServers`; the upstream serena needs a distinct name (e.g. `serena-semantic`) to avoid collision.
**Status**: RESOLVED 2026-08-18 — installed via `uv tool install -p 3.13 serena-agent` (v1.7.0), wired into `HKCU:\SOFTWARE\Policies\Claude\managedMcpServers` as `serena-semantic` using canonical `serena start-mcp-server --context=desktop-app` form. MCP initialize smoke-test returned `serverInfo.name=Serena, version=1.28.1`. Backup of previous registry value at `%TEMP%\registry_backup_2026-08-18.json`.

## 2026-08-22 — Layered audit and docs polish

**Tried**: Ran four passes over the repository: documentation consistency, static analysis, bug audit, and stale/cleanup review.
**Result**: `AGENTS.md` tool list and `minimax-coding-plan` naming corrected; `minimax-mcp-server/server.py` flake8 line-length issues resolved; all 26 proxy e2e tests and 17 media MCP tests pass; `py_compile` and `flake8` clean for core Python files.
**Why**: The 2026-08-18 bug audit (`docs/admin-gateway-audit/06-bugs-and-polish.md`) is now largely resolved in the proxy, but the document still lists many items as open. Tracked `.claude/skills/*.backup-*` directories and the stale bug audit as remaining cleanup.
**Lesson**: Do not delete tracked stale backup directories or rewrite `06-bugs-and-polish.md` without explicit user approval; record them in the handoff.
**Status**: resolved / pending user approval for destructive cleanup `%TEMP%\registry_backup_2026-08-18.json`.
## 2026-08-30 — Retire destructive automation; verify the native client

**Tried**: Compared Grok archive, active/older sources, scheduled tasks, services and official upstream docs. Replaced gateway transport/lifecycle and wired six pinned direct MCPs.
**Result**: Watchdog/health tasks disabled; services manual with restricted virtual accounts and Windows job limits. Offline gateway tests and direct six-MCP/SSH acceptance pass. Native tests exposed effective-policy and filesystem schema incompatibilities, corrected explicitly.
**Why**: A connected tool list and successful registry write did not establish a usable native client. Earlier shape-only proxy tests did not establish streaming/error behavior.
**Lesson**: No automatic repairs, broad process stops, bypass permissions or plaintext secret reports. Preserve stock Claude execution; keep adapters request-driven. Explicit isolated FastAPI/httpx dependencies replace the old stdlib-only preference because the Responses ASGI transport is now exercised and bounded.
**Status**: Safety repairs applied; release evidence must state native-test and platform limitations honestly. Historical entries above describe earlier builds and do not authorize restoring supervisors.

## 2026-08-30 — Native acceptance and published safety candidate

**Tried**: Tested stock Desktop coding, filesystem, browser, docs/search, voice catalogue, SSH and WSL. Exercised exact-window accessibility input in a disposable WinForms fixture. Ran Windows/Linux CI on Python 3.11/3.14.
**Result**: Native Windows SetValue/Invoke and final static-label read-back pass. 51 offline Python tests and three schema tests pass; all four CI jobs pass. Latest deployed gateway routes complete successfully. Final evidence is in docs/RELEASE_VALIDATION.md.
**Why**: Real native tests exposed omitted static labels, skipped window enumeration with use_ui_tree=false, and focus refusal. Windows CI exposed a socket reset on overloaded rejection; bounded half-close/drain fixes it. Static labels and semantic controls now allow verification without forced focus.
**Lesson**: Prefer exact named accessibility controls. Do not bypass focus restrictions or attach input queues. A metadata-only Snapshot is not proof of Windows input. Keep the expired GitLab credential private; the reviewed safety branch is published to the authorized GitHub repository with its original history preserved.
**Status**: Core acceptance complete; optional editor bridges, Cowork VM, paid generation, fresh-host install and long-duration soak remain explicitly unverified. Never turn those limitations into automatic repair loops.

## 2026-08-30 — Respect explicitly selected native permissions

**Tried**: Investigated repeated Write prompts despite the user's Bypass permissions selection. Compared the actual machine policy with Anthropic's configuration reference.
**Result**: Our bare builtin `ask` rules and MCP wildcard `ask` rules override native modes and standing approvals. The user explicitly authorized automatic approval. The generator now retires these old overrides, preserves other rules and exact blocks, and allows MCP standing grants. It does not choose a native mode or approve a pending call.
**Why**: Gateway containment and preventing watchdog repairs do not require interrupting every user-requested file edit. Bypass remains powerful and is not an OS sandbox.
**Lesson**: Keep resource/process limits separate from native task permissions. Never silently restore forced per-call prompts after this explicit user choice. Save work and reopen the client normally to reload the managed profile; do not kill an active coding task.
**Status**: Applied with a local backup. Before/after checks confirmed exactly three policy values changed; credentials, connection/model fields, six server commands, client preferences and explicit tool blocks were preserved. A second preview is idempotent. The user was asked to save work and reopen Claude normally; no active session was terminated. Native behavior after that reload is not yet observed.
