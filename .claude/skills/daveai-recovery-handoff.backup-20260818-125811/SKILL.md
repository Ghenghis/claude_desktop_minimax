---
name: daveai-recovery-handoff
description: Preserve exact project progress so an agent can recover after crash, compaction, context loss, process kill, or model handoff without restarting or asking the user to repeat work.
---

# Recovery and Handoff

At meaningful milestones and before risky operations update `.agent/PROJECT_STATE.md`:
- goal and acceptance criteria;
- last known good state;
- active worktree/artifact/device;
- completed gates;
- current failing test and evidence path;
- exact next action;
- rollback location;
- open blockers.

Do not store long transcripts. Store decisions, facts, paths and proof references. On resume, read this file and the proof ledger before taking action.
