---
name: daveai-capability-doctor
description: Detect, verify, repair, or route around missing development and reverse-engineering capabilities without making the user manually diagnose toolchains. Use when a command/tool/server fails, a dependency is missing, or the agent is about to ask the user to install something.
---

# Capability Doctor

1. Capture exact failure, command, exit code and relevant log first.
2. Check whether an already-enabled tool can solve the same objective.
3. Verify prerequisite executable/version/path/config.
4. Prefer repair over adding another overlapping framework.
5. Before installing third-party software, identify upstream repo, install method, rollback, privileges and network effects.
6. Never place secrets in command history/config examples.
7. Smoke-test the repaired capability.
8. After the same failure twice, stop repeating. Change hypothesis/tool or surface a concise blocker.
9. Record result in `PROOF_LEDGER.md`.
