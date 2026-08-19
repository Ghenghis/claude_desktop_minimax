# Project Principles — Admin Gateway

This file is always-loaded context for any agent (Claude Code, Task tool subagents, MCP
servers) working in this repo. Edit it rarely; deviations from these principles require
an explicit decision recorded in `.claude/notes.md`.

## Core principles

### 1. Security first — never weaken key handling
- The proxy must **always** override client-supplied `Authorization` / `X-Api-Key` with
  the key from `G:\private\.env`. This is the load-bearing invariant in
  `claude-minimax-proxy.py:206-214`. Any new endpoint, retry path, or auth shortcut
  must preserve it.
- Never log or echo the API key. Never write it to disk outside `.env`.
- Never bypass the `.env` ACL hardening. `Harden-MinimaxEnv.ps1` runs once and is
  not optional.

### 2. Stdlib-only by default
- The proxy's selling point is "no `pip install`". New Python code should use
  stdlib unless an explicit decision is recorded in `.claude/notes.md`.
- Acceptable exceptions (must be justified in `.claude/notes.md`):
  `cryptography` (for Ed25519 C2PA provenance), `Pillow` (for image manipulation).
- Adding a dep requires updating `requirements.txt` if/when it exists.

### 3. Fail closed, fail loudly
- If `.env` is missing or unreadable, the proxy must exit at startup with a clear
  message. Don't accept requests only to return 401.
- If a required upstream endpoint is unreachable, return 502 with the underlying
  error in the body — never swallow exceptions silently.
- If a new endpoint is requested but not implemented, return 404 with the path —
  never 200 with empty body.

### 4. Comments only where the WHY is non-obvious
- No `# loop through messages` style comments.
- Yes: `# Strip client auth — Claude Desktop sends a placeholder that MiniMax rejects`
  (explains WHY a non-obvious line exists).
- If removing the comment wouldn't confuse a future reader, remove it.

### 5. Test before claiming done
- After any Edit or Write to a `.py` file, run `.claude/verifiers/run.sh`.
- After any Edit to a `.ps1` file, run it with `-WhatIf` or a no-op equivalent.
- If a verifier fails, do not declare the work complete.

### 6. Cross-platform portability on Windows is required
- This codebase runs on Windows (PowerShell + Python). No bash-only idioms.
- Python code must work with `python.exe` from a standard install.
- Path separators: prefer `os.path.join` and `pathlib.Path`; never hard-code `/` or `\`.

### 7. Don't add features beyond what was asked
- A bug fix doesn't need surrounding cleanup. A one-shot operation doesn't need a
  helper. Three similar lines is better than a premature abstraction.
- If you find yourself wanting to refactor unrelated code, stop — that's a separate
  task and should be tracked separately.

### 8. Backwards compatibility is load-bearing for the registry
- `inferenceGatewayBaseUrl=http://127.0.0.1:48217/anthropic` must not change.
- `inferenceGatewayApiKey=proxy-managed` must remain the literal placeholder.
- The 4 Anthropic-looking picker slots (`claude-sonnet-4-5`, etc.) are wired to
  MiniMax via `MODEL_MAP`. New slots are fine; breaking existing slots is not.

## Style quick-reference

- Python: PEP 8, type hints on new functions, `snake_case` for functions/variables,
  `PascalCase` for classes. f-strings, not `.format()`. `pathlib.Path` over
  `os.path`. No `print()` in production paths; use `print(..., file=sys.stderr)`
  for diagnostics.
- PowerShell: `Set-StrictMode -Version Latest`, `PascalCase` for functions,
  `$camelCase` for variables, `Write-Host` for user-facing output,
  `Write-Warning` / `Write-Error` for failures.
- Tests: one assertion focus per test, descriptive name, no I/O outside `tests/`.

## What lives in `.claude/notes.md`

- "Tried X, failed because Y" — so the next agent doesn't retry the same dead end.
- "Open decision: do we ship A or B?" — so the next agent knows to ask the user
  instead of picking.
- "Last verified: <date> <gate> passed" — so the next agent knows what's current.