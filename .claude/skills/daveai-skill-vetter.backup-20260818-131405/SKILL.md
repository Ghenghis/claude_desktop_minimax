---
name: daveai-skill-vetter
description: Vet a third-party Claude skill, plugin, MCP server or marketplace before installation or promotion to a default profile. Use whenever a new agent extension is proposed.
---

# Skill / Plugin / MCP Vetter

1. Resolve the real upstream repository and record revision/tag.
2. Inspect the manifest, `SKILL.md`, hooks, MCP config, install/update scripts and executable entry points.
3. List capabilities: filesystem read/write, shell/process, network, credentials/env, browser/device/debugger control, persistence, external writes.
4. Flag any hidden download/execute, credential access, prompt override, auto-publish, telemetry, remote binding or writes outside intended scope.
5. Check whether the capability duplicates an already trusted tool.
6. Prefer tagged/pinned versions for long-lived project harnesses.
7. Smoke-test in a disposable project/profile.
8. Record uninstall/rollback.
9. Do not promote to CORE unless the benefit is clear and the risk surface is acceptable.
