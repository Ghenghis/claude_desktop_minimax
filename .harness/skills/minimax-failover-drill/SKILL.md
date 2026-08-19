---
name: minimax-failover-drill
description: |
  Simulate MiniMax upstream 5xx and verify the proxy's Model Chains
  waterfall falls through to the next model. Use to verify failover
  works after any change to claude-minimax-proxy.py.
when_to_use: |
  Trigger: after any change to MODEL_CHAINS or pick_minimax_model,
  after MiniMax has a known outage, or during chaos testing.
  Don't trigger: in production (this generates real MiniMax load).
inputs:
  - name: picker
    type: string
    required: true
    enum: [sonnet, opus, haiku]
    description: Which picker slot to drill on.
  - name: inject_failure
    type: string
    required: false
    enum: [none, "5xx", "429", "timeout"]
    default: "5xx"
    description: Which upstream failure mode to simulate.
  - name: dry_run
    type: boolean
    required: false
    default: false
outputs:
  - Chat log showing each chain hop, its status, and final outcome.
---

# Procedure

1. Set up a local mock MiniMax endpoint that returns the chosen `inject_failure`
   for the primary chain model and 200 for every other model.
   - Use `--offline` mode (P1 implementation) plus a stub that inspects the
     `model` field and returns 503 for `<primary>`.
2. Send 1 real Anthropic-format POST to `/v1/messages` with `model: claude-sonnet-4-5`.
3. Capture and print the chain hop log:
   ```
   [chain] picker=claude-sonnet-4-5 attempt 1/3 model=MiniMax-M3
   [chain] model=MiniMax-M3 returned 503; falling through
   [chain] picker=claude-sonnet-4-5 attempt 2/3 model=MiniMax-M2.7
   [chain] model=MiniMax-M2.7 returned 200; chain succeeded
   ```
4. Assert: final status is 200; primary was tried first; fallback was tried second;
   the chain stopped as soon as one model succeeded.

# Examples

```
/minimax-failover-drill --picker=sonnet --inject_failure=5xx
/minimax-failover-drill --picker=haiku --inject_failure=429
```

# Limitations

- Requires `--offline` mode (P1) AND a configurable mock MiniMax server (P1).
- Until those land, this skill runs against the real MiniMax (charges quota).
- Does not verify the Retry-After path (P0 #3); covers chain failover only.