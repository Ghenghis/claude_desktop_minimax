---
name: daveai-skill-vetter
description: Vet a skill, plugin, or MCP before installing or enabling it.
---

# daveai-skill-vetter

**Use when:** a third-party tool, skill, plugin, or MCP server is about to be installed or enabled for the first time

## Steps
- Resolve the upstream URL and record the exact revision/commit hash.
- Inspect the top-level README, manifest, and entry-point script.
- List every file the tool can read, write, execute, or network-call.
- Check for hardcoded credentials, shell-execution of user input, or network exfiltration.
- Smoke-test the tool on a harmless target and capture the result.
- Write a risk/capability summary and a rollback method to the proof ledger.

## Proof required
vetter report with revision, risk flags, and smoke-test evidence
