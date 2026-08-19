---
name: daveai-web-e2e
description: Design and run deterministic web, PWA, or Electron end-to-end tests.
---

# daveai-web-e2e

**Use when:** a web-accessible user flow needs repeatable proof or repair

## Steps
- Select the smallest test tool: Playwright CLI/Skills first, MCP only for long loops.
- Record the critical user flow as a step list.
- Write or edit the Playwright/Maestro test file.
- Run the test, capture a trace or screenshot on failure.
- Confirm the test fails before the fix and passes after.

## Proof required
passing test run with replay trace or failure screenshot
