# Project Charter — Admin Gateway

This file is automatically loaded as system-prompt context for every Claude Code
session in this repo. It tells Claude what this project is, what's done, and what
the standing rules are.

## What this project is

A local Windows-side proxy (`claude-minimax-proxy.py`) that lets Claude Desktop talk
to MiniMax's API. The proxy is on `127.0.0.1:48217`; Claude Desktop is configured
via `HKCU:\SOFTWARE\Policies\Claude` registry keys (see `Set-ClaudeDesktopGateway.ps1`).

Companion PowerShell scripts handle setup, registry wiring, key loading, ACL hardening,
watchdog, and end-to-end testing.

## Always-loaded references

- `.claude/principles.md` — the project's core rules (security, stdlib-only, fail-closed).
  Read before any non-trivial change.
- `.claude/notes.md` — the project notebook. **Update it whenever you**:
  - Try something that failed (so the next agent doesn't retry it)
  - Make a decision between alternatives (so the next agent doesn't re-ask)
  - Complete a verification gate (so the next agent knows what's current)

## Maintenance rituals

### After every Edit or Write to a `.py` file
```bash
bash .claude/verifiers/run.sh <path-to-edited-file>
```
This runs `python -m py_compile` then `flake8 --max-line-length=120`. If either fails,
fix it before continuing. **Do not declare work complete with a failing verifier.**

### Before declaring work complete
- `bash .claude/verifiers/run.sh claude-minimax-proxy.py` — exits 0?
- `python tests/test_proxy_e2e.py` — all tests pass?
- `.claude/notes.md` updated with the latest verification timestamp and gate status?

### Before pushing or committing
- Run `bash .claude/verifiers/run.sh` (no argument) to verify all `.py` files
- Run `python -m pytest tests/` (when pytest is available; otherwise run the
  e2e test directly)

## "Build me X" prompt template (from Vercel/v0 pattern)

When the user asks for a non-trivial build, fill in three elements before starting:

```
What:    <the artifact — landing page, dashboard, microservice, etc.>
For:     <who uses it, in what moment, to do what>
Constraints: <platform, visual tone, layout, libraries>
```

If any element is missing, ask before starting. Don't guess.

## Current state (live, not aspirational)

- **Working**: `/v1/messages` (Anthropic-compat text), 4 picker slots wired, watchdog,
  ACL hardening, end-to-end test (`Test-ClaudeMiniMaxSetup.ps1`).
- **New endpoints shipped**: `/v1/chat/completions` (OpenAI-compat), `/v1/image_generation`
  (sync T2I via `image-01`). All Bearer-auth, all proxy the `OPENAI_BASE`
  constant at `claude-minimax-proxy.py:30-31`.
- **Not yet shipped**: speech/TTS, async video gen, voice clone, music gen, file mgmt.
- **Open bugs**: see `docs/admin-gateway-audit/06-bugs-and-polish.md` — 30 items, 5 critical.

## Architecture one-liner

```
Claude Desktop (3P gateway mode, port 48217/anthropic)
  -> claude-minimax-proxy.py (stdlib HTTP, ThreadingHTTPServer)
       -> MiniMax API: /anthropic/v1/messages (X-Api-Key)
                     /v1/chat/completions, /v1/image_generation, ... (Authorization: Bearer)
       <-  always inject key from G:\private\.env, discard client auth
```

## When in doubt

1. Read `.claude/principles.md` first.
2. Check `.claude/notes.md` for prior decisions on the same topic.
3. Run `.claude/verifiers/run.sh` before claiming something works.
4. If still stuck, ask the user — don't guess on security or auth code.