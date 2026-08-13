---
name: claude-permission-repair
description: |
  Diagnose and repair the Claude Desktop "Bypass permissions" UI bug
  (anthropics/claude-code #61304). Use when the user reports that the
  permission-mode toggle fails with "Permission mode couldn't be changed."
when_to_use: |
  Trigger: user pastes the error message, says "bypass permissions broken",
  says "accept edits but not bypass".
  Don't trigger: when the user is on a Mac (not yet affected) or on a
  Claude Code CLI session (use `--dangerously-skip-permissions` directly).
inputs:
  - name: dry_run
    type: boolean
    required: false
    default: false
    description: If true, only diagnose; don't write any files or registry values.
outputs:
  - Chat log with diagnosis steps and (if not dry_run) which fix was applied.
---

# Procedure

1. Detect the error: check `%APPDATA%\Claude\logs\main.log` for the line
   "Permission mode couldn't be changed" OR look for the user's pasted error message.
2. Check `HKCU:\SOFTWARE\Policies\Claude\permissionMode` (Windows registry).
   - If missing or `"default"`, that's the bug — desktop app spawns CLI with
     `--permission-mode default` instead of bypass.
3. Apply the fix from `Fix-ClaudePermissions.ps1`:
   - Set `permissions.defaultMode = "bypassPermissions"` in `%APPDATA%\Claude\settings.json`.
   - Generate the `Start-ClaudeCode-BypassPermissions.ps1` launcher as a backup.
4. Verify by re-launching Claude Desktop and checking that the toggle now persists.
   (Cannot verify directly from the skill; instruct the user to test.)
5. If `dry_run`, print steps 1-3 only; do not write anything.

# Examples

```
/claude-permission-repair
/claude-permission-repair --dry_run
```

# Limitations

- Cannot restart Claude Desktop from the skill (would need admin or user gesture).
- Verification is partial: skill confirms the registry + settings file are written;
  user must confirm the UI toggle now works.
- Workaround (manual launcher with `--dangerously-skip-permissions`) is always
  available; the skill sets it up automatically.