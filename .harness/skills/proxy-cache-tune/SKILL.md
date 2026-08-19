---
name: proxy-cache-tune
description: |
  Analyze proxy cache hit-rate logs and recommend TTL changes.
  Use when the user asks "is the cache working", "should I bump the TTL",
  or "how much quota am I saving with caching".
when_to_use: |
  Trigger: any question about cache effectiveness.
  Don't trigger: when the cache hasn't been hit yet (insufficient data).
inputs:
  - name: window
    type: string
    required: false
    description: Relative window like '24h', '7d'. Defaults to '24h'.
  - name: dry_run
    type: boolean
    required: false
    default: false
outputs:
  - Markdown table with hit-rate, miss-rate, and TTL recommendation.
---

# Procedure

1. Locate cache log lines. The proxy emits cache events via stderr in this format
   (after P0 #2 lands):
   ```
   [cache] HIT key=<sha256[:12]> model=<model>
   [cache] PUT key=<sha256[:12]> model=<model> size=<bytes>
   ```
   If those don't exist yet, the cache isn't being instrumented; the skill reports
   that and stops.
2. Count HIT vs PUT in the requested window. HIT-rate = HIT / (HIT + PUT).
3. If HIT-rate < 20%, recommend `MINIMAX_CACHE_TTL_SECONDS` *decrease* (shorter TTL →
   fewer stale entries) — but flag that low hit-rate usually means cache keys are wrong,
   not that TTL is wrong.
4. If HIT-rate > 70%, recommend *increase* TTL (24h → 48h or 7d) to capture longer-tail
   repeat requests.
5. Print recommendation in chat; do NOT change env vars automatically (still WIP;
   require explicit user confirmation before editing anything).

# Examples

```
/proxy-cache-tune
/proxy-cache-tune --window=7d
/proxy-cache-tune --window=24h --dry-run
```

# Limitations

- Requires the proxy to instrument cache events (added in P0 #2; pre-P0 this skill is a no-op).
- Currently can't auto-apply TTL changes; the user must edit env vars and restart.