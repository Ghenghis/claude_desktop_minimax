---
name: daveai-web-e2e
description: Verify web, PWA and Electron browser-accessible user flows using Playwright CLI + skills, producing deterministic traces/screenshots and a fail-closed proof result.
---

# Web/PWA/Electron E2E

1. Prefer `playwright-cli` + installed skills for normal coding-agent tests.
2. Start from a clean named session or known state.
3. Exercise the user-critical flow, not just page load.
4. Assert observable state after each important transition.
5. Capture console/network output when diagnosis requires it.
6. On failure, save trace/screenshot/snapshot before repair.
7. Repair, then replay the full critical path from a clean session.
8. Use Playwright MCP only when persistent exploratory page state materially helps.
9. Add evidence paths and result to `.agent/PROOF_LEDGER.md`.
