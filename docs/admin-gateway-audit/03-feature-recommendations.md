# Admin Gateway — Prioritized Feature Recommendations

Scope: local Python proxy at `127.0.0.1:48217` that fronts `https://api.minimax.io/anthropic` for Claude Desktop on Windows. Single user. Source: `claude-minimax-proxy.py` (267 lines, stdlib only). Companion scripts: `Start-ClaudeMiniMaxProxy.ps1`, `Watch-ClaudeMiniMaxProxy.ps1`, `Set-ClaudeDesktopGateway.ps1`, `Set-ClaudeDesktopInference.ps1`, `Test-ClaudeMiniMaxSetup.ps1`, `Harden-MinimaxEnv.ps1`, `Load-MinimaxKey.ps1`.

## 1. Executive summary

The Admin Gateway is a tiny stdlib-only proxy (`claude-minimax-proxy.py`) that solves one specific problem: Claude Desktop 1.6259+ rejects non-Anthropic model names in `inferenceModels`, so the proxy accepts Anthropic-looking names, rewrites them to `MiniMax-M3` (or M2.7/M2.1 via `MODEL_MAP` at lines 93-102), and forwards verbatim — while **always** overriding the client-supplied `Authorization`/`X-Api-Key` with the real key loaded from `G:\private\.env` (lines 206-214). That override is the single most important behavior to preserve; every recommendation below is constrained by it. The proxy is missing the operational features a single user actually needs day-to-day: log redaction is line-level only, the key is re-read from disk on every request (no cache), there is no retry/backoff, no per-model quota visibility, no circuit breaker, and the admin surface is zero (no `/health`, no `/ready`, no metrics). Top three priorities: (P0) a `/health` endpoint plus safe startup key validation, (P0) persistent structured request logs with secret-redaction, (P1) in-memory key cache + disk-`mtime` invalidation, (P1) retry-with-backoff and transparent failover to `MiniMax-M2.7` on upstream 5xx.

## 2. Prioritized recommendations

### P0 — must-have, low effort (<1 day each)

**P0-1. `/health` and `/ready` admin endpoints**
- **Problem**: `Watch-ClaudeMiniMaxProxy.ps1` polls port 48217 every 15s but can only detect "port open / port closed" (line 14-17). A process that has hung inside `urlopen` (e.g. mini-max hung on a single request) leaves the socket open yet non-functional; Claude Desktop then hangs for `timeout=180` with no signal.
- **Target user**: single operator running the watchdog.
- **Effort**: 2-3 hours.
- **Implementation**: add `do_GET("/healthz")` and `do_GET("/readyz")` to `Handler` in `claude-minimax-proxy.py`. `/healthz` returns `200 {"status":"ok"}` always (cheap liveness). `/readyz` returns `200 {"key":bool,"upstream":bool,"last_ok_ts":<int>}` by checking `load_minimax_key() is not None` and tracking `self._last_ok_ts = time.time()` after each successful `_proxy_messages`. Add a 1-second in-process cache on `load_minimax_key` keyed by `(path, mtime)` to avoid re-reading `.env` on every probe. Update `Watch-ClaudeMiniMaxProxy.ps1` to issue `Invoke-RestMethod http://127.0.0.1:48217/readyz` instead of `Test-NetConnection`.
- **Rationale**: minimal surface, no new dependencies, eliminates the silent-hung-process class of failure that the current watchdog cannot catch.
- **Risks**: very low. Do not expose key length or any path info in the response body — `{"key":true|false}` only.

**P0-2. Structured request log with secret-redaction**
- **Problem**: `log_message` (line 110-111) writes `"<datetime> POST /v1/messages HTTP/1.1 200 -"` to stderr. That's fine, but there is no per-request duration, no upstream latency split, no request-id, and no way to grep `AICE_DATA/claude-minimax-proxy.err` for failures. The existing `[key-path]` lines at 208 and 212 are inconsistent (some print, some don't).
- **Target user**: operator debugging failed Claude Desktop chats.
- **Effort**: 4-6 hours.
- **Implementation**: in `_proxy_messages`, set `self._t0 = time.monotonic()`, capture `resp.status` and `time.monotonic() - self._t0`. Wrap the print in a single `log_event(kind, fields)` helper that emits JSON lines to stderr. Add a redaction filter: drop any header named `authorization`/`x-api-key` and any JSON key matching `(?i)(api[_-]?key|secret|token|bearer)` before logging. New file `claude-minimax-proxy-logger.py` (or top-of-file section) keeps diff small.
- **Rationale**: zero new deps; transforms an unstructured stderr stream into one JSON line per request that `Select-String | ConvertFrom-Json` can consume. Foundation for every later observability feature.
- **Risks**: must be reviewed line-by-line; a missed redaction leaks the key. Add a unit test (`tests/test_log_redaction.py`) that asserts a fake `X-Api-Key: sk-abc123` is not present in the captured stderr.

**P0-3. Startup key validation with fail-fast**
- **Problem**: `load_minimax_key()` is called inside `_proxy_messages` (line 209). If the .env is missing or unreadable, the proxy happily accepts `/v1/messages`, injects nothing, and lets MiniMax return a 401. The user sees Claude Desktop's generic "request failed" with no actionable signal.
- **Target user**: operator after editing `G:\private\.env` or applying a Windows Update that resets ACLs.
- **Effort**: 1-2 hours.
- **Implementation**: in `main()` (line 254), call `load_minimax_key()` once before `serve_forever()`. If it returns `None`, print `[key-path] FATAL: G:\private\.env missing or MINIMAX_API_KEY not set` to stderr and `sys.exit(2)`. Reuse `Start-ClaudeMiniMaxProxy.ps1`'s `$env:MINIMAX_ENV_FILE` already wired at line 9. Tighten `Harden-MinimaxEnv.ps1` so a denied ACL is detected at boot, not at first chat.
- **Rationale**: shifts failure from "first chat fails mysteriously" to "proxy refuses to start" — exactly the right ergonomic.
- **Risks**: none, provided the fatal message does not echo the path of every candidate (only the resolved one).

### P1 — should-have, moderate effort (1-5 days each)

**P1-1. Retry-with-backoff and transparent failover**
- **Problem**: a single `urlopen(req, timeout=180)` (line 217) means any transient MiniMax 5xx or connection reset fails the request. Claude Desktop sometimes retries, but only with the same payload — wasting user's input tokens if the failure was upstream-only.
- **Target user**: single user during MiniMax regional outages.
- **Effort**: 2 days.
- **Implementation**: extract `_proxy_messages` body into `_call_upstream(payload)` that wraps `urlopen` in a 3-attempt loop: delays `0.5, 2, 5` seconds; retries on `HTTPError` with `code in {408, 425, 429, 500, 502, 503, 504}` and on `URLError`; never retries on 4xx other than 408/425/429. Track attempts in the structured log. No model fallback (P2 territory).
- **Rationale**: closes the biggest gap vs. LiteLLM/Portkey/CF-AI-GW at minimal code.
- **Risks**: must cap total wait ≤ 60s so it does not exceed Claude Desktop's own timeout. Set `Retry-After` header parsing if present.

**P1-2. Per-model cost / token ledger**
- **Problem**: there is no way to see how many tokens each picker slot (`claude-sonnet-4-5` → M3, `claude-opus-4-6` → M2.7, `claude-haiku-4-5` → M2.1) has consumed this session.
- **Target user**: single user paying out of pocket.
- **Effort**: 2-3 days.
- **Implementation**: capture `usage.input_tokens` / `usage.output_tokens` from upstream JSON (SSE aggregate event) and from non-streaming responses. New SQLite table `usage(ts, picker_model, minimax_model, input_tok, output_tok)` in `AICE_DATA/proxy-usage.sqlite`. Add `GET /admin/usage?since=<iso>` that returns last 24h totals per model. Guard with `127.0.0.1`-only binding (already the case) plus a `X-Admin-Token` header check populated from `MINIMAX_ADMIN_TOKEN` env var.
- **Rationale**: real budget visibility, no third-party dependency (stdlib `sqlite3`).
- **Risks**: the admin endpoint must never accept a request from a non-loopback interface. Reject anything that did not come from `127.0.0.1`/`::1`.

**P1-3. In-memory key cache with `.env` `mtime` invalidation**
- **Problem**: `load_minimax_key()` is called on every `/v1/messages` (line 209), which re-parses `G:\private\.env` from disk each time. Cheap but pointless, and it means rotating the key (e.g. after a suspected leak — see `docs/Claude-Desktop-MiniMax.md` lines 201-208) requires a proxy restart.
- **Target user**: operator after key rotation.
- **Effort**: 0.5 day.
- **Implementation**: module-level `_key_cache = {"path": None, "mtime": 0.0, "key": None}`. Refactor `load_minimax_key()` to first `os.stat(path).st_mtime`; if same as cached, return cached value. On key rotation, the operator edits the file and the **next** request picks up the new key automatically.
- **Rationale**: tiny diff, big quality-of-life win.
- **Risks**: ensure the cache key is `(path, mtime_ns)` so sub-second edits invalidate.

### P2 — nice-to-have, larger effort (1+ weeks)

**P2-1. LiteLLM-parity virtual-key + per-route budget**
Add the ability to mint a short-lived virtual key (`X-Api-Key: vkey_<rand>`) stored in a second `vault.json` ACL'd to `G:\private`. Each route in `MODEL_MAP` gets a daily token budget; on exceed, return `429 {"error":"daily_quota_exceeded","model":"MiniMax-M3"}` and switch to a fallback model (M2.7). This is the LiteLLM/Portkey "virtual keys + budgets" feature in miniature, scoped to one user. Effort: 1-2 weeks. Risk: must not weaken the existing `.env`-key override semantics.

**P2-2. Multi-provider failover**
Add a second `TARGET_BASE` for an OpenAI-compatible MiniMax endpoint (`https://api.minimax.io/v1`). Failover only fires on P1-1's exhausted retries. Adds the request-shape translation (Anthropic → OpenAI Chat Completions). Effort: 2 weeks. Risk: doubles the surface area; ensure SSE event formats stay compatible with Claude Desktop's parser.

**P2-3. OTel traces to local console**
Pipe the existing P0-2 structured log into an OTel exporter over OTLP/HTTP to a local collector (`127.0.0.1:4318`). Only worth doing once P0-2 is stable. Effort: 1 week.

## 3. Cross-cutting implementation considerations

- **Security** — every new code path must go through the same redaction discipline as `_proxy_messages`. New helper `_safe_log_dict(d)` recursively scrubs keys matching `(?i)(api[_-]?key|secret|token|bearer|password)`. Unit test it.
- **Backwards compatibility** — the registry write in `Set-ClaudeDesktopInference.ps1` line 17 (`inferenceGatewayApiKey=proxy-managed`) is load-bearing; do not change `http://127.0.0.1:48217/anthropic` (line 15) or Claude Desktop's auto-config will silently re-prompt.
- **Deployment** — extend `Watch-ClaudeMiniMaxProxy.ps1`'s log path to include the new structured JSON stream (e.g. `AICE_DATA/claude-minimax-proxy.jsonl`) and add a `claude-minimax-proxy.err` size-rotate guard so logs cannot fill the disk.
- **Dependency policy** — keep stdlib-only as long as possible. The proxy's selling point is "no `pip install`". If `sqlite3` is needed (P1-2) it is already in stdlib. Anything beyond needs an explicit decision.

## 4. Gaps and risks introduced by adding features

1. **Breaking the patched proxy's "always inject .env key" behavior** (lines 206-214). Every retry/cache/path that touches auth must preserve unconditional override. Add a regression test in `Test-ClaudeMiniMaxSetup.ps1` that sends `Authorization: Bearer fake` and asserts the upstream still gets the `.env` key.
2. **Secret leakage via new endpoints**. `/admin/usage` (P1-2) and `/admin/rotate-key` (any future) must bind to loopback only and require a token. Add `SO_REUSEADDR` is fine; do **not** bind to `0.0.0.0` ever.
3. **Accidentally enabling outbound internet that wasn't there before**. The proxy already calls `https://api.minimax.io/anthropic` (line 30). New endpoints (OpenAI-compat, OTel collector, health probes) must each be added to a single allowlist constant; default-deny any other host.
4. **Persistent log growth**. JSONL is denser than the current single-line format; rotate at 10MB or 7 days.
5. **ACL regression on `G:\private\.env`** — `Harden-MinimaxEnv.ps1` runs once. If a feature later caches the key in memory (P1-3) and the ACL is later widened, the cached key keeps working. Mitigate by re-checking file ownership in `load_minimax_key` on cache miss.
6. **Test flakiness** — `Test-ClaudeMiniMaxSetup.ps1` line 48-58 makes a live API call. New tests must follow that pattern (real proof) rather than mock, because the value of this proxy is "actually forwards to MiniMax correctly".

## 5. Suggested order of operations (one-weekend MVP)

Ship these three, in this order:

1. **P0-3 startup key validation** (1-2 hours). Pure fail-fast win.
2. **P0-1 `/healthz` + `/readyz` + watchdog upgrade** (2-3 hours). Detects hung processes.
3. **P0-2 structured JSON log + redaction test** (4-6 hours). Foundation for everything else; the redaction test makes subsequent secret-touching features safe.

That leaves Sunday for P1-3 (key cache, 0.5 day) and the start of P1-1 (retry skeleton). Total ≈ 1.5 weekend days of work; everything else is incremental after that.