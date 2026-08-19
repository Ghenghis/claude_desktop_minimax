---
name: daveai-capability-doctor
description: Diagnose why a tool is missing, failing, or not exposed to the agent.
---

# daveai-capability-doctor

**Use when:** a tool that should be available is not listed, not responding, or failing

## Steps
- Confirm the command is on PATH and the version is recent.
- Check the MCP/connector config for the correct command, args, and env.
- Run the tool with --version or a minimal no-op command.
- Inspect the latest error log or transport message.
- Propose one minimal fix and a fallback if the fix fails.

## Proof required
diagnostic report with PATH check, command test, and proposed fix
