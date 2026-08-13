---
name: minimax-cost-report
description: |
  Produce a daily cost report for the Admin Gateway from log files.
  Use when the user asks "how much did I spend today", "what did I
  burn on MiniMax", or "show me yesterday's token counts".
when_to_use: |
  Trigger: any cost / spend / usage / token question about the gateway.
  Don't trigger: when the user wants live quota from MiniMax (that needs
  a real `/v1/me/balance` endpoint, not yet implemented).
inputs:
  - name: since
    type: string
    required: false
    description: ISO-8601 lower bound; defaults to 24h ago.
  - name: window
    type: string
    required: false
    description: Relative window like '24h', '7d'. Overrides `since` if both set.
  - name: dry_run
    type: boolean
    required: false
    default: false
outputs:
  - Markdown table printed to chat.
  - Optional sidecar file at AICE_DATA/cost-report-<ts>.md.
---

# Procedure

1. Locate the proxy log files:
   - `G:\Github\claude-codex-devin\AICE_DATA\claude-minimax-proxy.out`
   - `G:\Github\claude-codex-devin\AICE_DATA\claude-minimax-proxy.err`
2. Parse stderr lines that match `[chain] picker=<model> attempt <n>/<m> model=<target>` to
   count chain hops per picker slot.
3. Parse stderr lines that match `[chain] model=<target> returned <status>` to count failures.
4. **NOTE**: usage/cost estimation is approximate. The proxy does not yet log `usage.input_tokens`
   / `usage.output_tokens` per request — that requires P1-2 (cost ledger). Today this skill
   produces a hop-count report, not a dollar-cost report.
5. Render the table:

```
| Picker slot | Chain hops | First-try success | Avg hops/request |
|-------------|-----------:|------------------:|-----------------:|
| sonnet     | N         | N%                | X.XX             |
| opus       | ...       | ...               | ...              |
| haiku      | ...       | ...               | ...              |
```

6. If `--dry-run` is set, print the table to chat but skip writing the sidecar file.

# Examples

```
/minimax-cost-report
/minimax-cost-report --window=7d
/minimax-cost-report --since=2026-08-01T00:00:00Z --dry-run
```

# Limitations

- No dollar figures yet (P1-2 not shipped).
- Reads proxy stderr only; if the proxy was launched directly (not via the watchdog),
  logs may be in a different location.
- Does not account for MiniMax plan tier; Ultra-plan users will see higher absolute counts.