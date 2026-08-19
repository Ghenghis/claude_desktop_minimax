---
name: playwright-verify
description: |
  Drive a real browser via Playwright to verify the Admin Gateway's UI surface
  (Claude Desktop picker, model selectors, Settings → Extensions → MCP servers
  list, /readyz page). Use after any change to the registry, watcher, or
  Claude Desktop config to confirm the user's UI actually reflects the new state.
when_to_use: |
  Trigger: "does the picker show X", "did MCP server registration stick",
  "screenshot the Claude Desktop Settings page", "verify the model list
  includes the new picker slot".
  Don't trigger: for non-UI smoke tests (use Test-ClaudeMiniMaxSetup.ps1
  or tests/test_proxy_e2e.py instead).
inputs:
  - name: url
    type: string
    required: false
    description: URL to navigate to. Defaults to the Claude Desktop Settings page.
  - name: selector
    type: string
    required: false
    description: CSS selector to assert. If omitted, captures full-page screenshot.
  - name: screenshot_path
    type: string
    required: false
    description: Where to write the screenshot. Defaults to AICE_DATA/playwright-<ts>.png.
  - name: dry_run
    type: boolean
    required: false
    default: false
outputs:
  - Screenshot file (PNG).
  - Chat log: selector found / not found + text content.
  - HermesProof evidence entry (success / failure).
---

# Procedure

1. Check Playwright availability: `npx playwright --version` (or `pwsh -c "Get-Module -ListAvailable Playwright"`).
   If not installed: install with `npm install -D @playwright/test && npx playwright install chromium`.
2. `hermes_anonymous_claim role=BUILDER ttl_minutes=10`
3. Launch headless Chromium via Playwright Python or Node bindings.
4. Navigate to `url` (default: Claude Desktop Settings — but Claude Desktop is
   an Electron app, not a website; for non-Chrome surfaces the skill uses the
   `readyz`/`healthz` HTTP endpoints instead).
5. If `selector` is set, wait for it (timeout 10s) and report whether it appeared.
6. Capture screenshot to `screenshot_path`.
7. If `dry_run`: print steps 1-6, do not write the screenshot, do not call hermes.
8. `hermes_append_evidence kind=playwright-verify summary="<result>"` with data containing the screenshot path.
9. `hermes_record_outcome merge` (or `reject` if the selector check failed).
10. `hermes_anonymous_release role=BUILDER`

# Examples

```
/playwright-verify --url=http://127.0.0.1:48217/readyz
/playwright-verify --url=http://127.0.0.1:48217/v1/models --selector=.model-name
/playwright-verify --dry_run
```

# Limitations

- Claude Desktop is an Electron app; Playwright cannot drive it directly without
  `_electron.launch()`. This skill primarily verifies the gateway's HTTP surface
  (where it shines) and uses Electron-specific code only when verifying Claude
  Desktop itself.
- Screenshot path is local; not encrypted at rest.
- Does not currently auto-upload screenshots to MCP Apps inline UI; that is a
  P1 enhancement (resource URI `ui://admin-gateway/playwright-result.png`).