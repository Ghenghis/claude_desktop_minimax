---
name: daveai-recovery-handoff
description: Safely stop work and hand off to another agent or the user when blocked.
---

# daveai-recovery-handoff

**Use when:** a task is blocked, the session is ending, or a different profile/agent is needed

## Steps
- Record the last completed gate and the next unresolved gate.
- Write a concise handoff note with current state and blockers.
- Store rollback instructions and the last known-good commit/hash.
- Release any held locks or resources.
- Update PROJECT_STATE.md with the handoff.

## Proof required
handoff note and updated PROJECT_STATE.md
