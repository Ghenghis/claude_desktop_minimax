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