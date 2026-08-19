---
name: daveai-proof-ledger
description: Enforce evidence-based completion for coding, UI, reverse engineering and automation tasks. Use whenever the agent is implementing, fixing, rebuilding, testing, packaging, or claiming a task is complete.
---

# Proof Ledger

A result is not DONE because files were edited.

For each acceptance criterion record:
- criterion;
- test/observation;
- command/tool;
- evidence path;
- PASS/FAIL/BLOCKED;
- timestamp;
- verifier.

Rules:
1. Build success is not UI/E2E success.
2. A fix must reproduce the old failure when possible and then pass after the change.
3. GUI/mobile behavior requires executable proof: deterministic automation, screenshots/trace/video/logs as appropriate.
4. Reverse-engineering claims require reproducible static or dynamic evidence.
5. Critical path must be repeated from a clean/restarted state by the verifier.
6. If evidence is missing, report NOT VERIFIED rather than DONE.
