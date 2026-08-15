# Codex + MiniMax Gateway Setup Audit

**Date:** 2026-08-14  
**Scope:** OpenAI Codex CLI / ChatGPT desktop app on Windows using the local `claude-minimax-proxy.py` gateway to reach MiniMax models.  
**Status:** Issues identified, corrections applied, proxy updated to support the Responses API; Claude Desktop and ChatGPT Codex verified working.

---

## Images reviewed

1. **Devin/Windsurf sidecar crash**  
   `Client windsurf: connection to server is erroring. Shutting down server.`  
   Root cause: the sidecar could not parse `C:\Users\Admin\.codex\config.toml` because it contained a duplicate table declaration.

2. **ChatGPT desktop Windows setup**  
   `Couldn’t check Windows setup` → `Windows setup didn’t finish · config_load` with a UAC prompt for `ChatGPT`.  
   Root cause: `config.toml` contained `wire_api = "chat"`, which Codex no longer accepts.  
   UAC must also be allowed (`Yes`) for the installer to complete.

---

## Issues found

### 1. Duplicate `env` table in `config.toml` (TOML parse failure)

`mcp_servers.hermes3d-locks` was declared with an inline `env = { ... }` table and then again as a separate `[mcp_servers.hermes3d-locks.env]` table.  
TOML does not allow the same key to be declared twice, so `tomllib` and the Rust parser used by Codex/Devin rejected the file.

**Impact:** Devin/Windsurf server crashed on start, and Codex could not load its configuration.

### 2. `wire_api = "chat"` is no longer supported by Codex

Online research (OpenAI Codex discussion #7782 and the `codex-rs/model-provider-info` source) confirms:

- `wire_api = "chat"` was removed in early 2026.
- The only valid value is `wire_api = "responses"`.
- Third-party gateways must implement `POST /v1/responses` or route through a translator such as `codex-relay`.

**Impact:** Codex failed config load (`config_load`) during Windows setup because the `WireApi` deserializer returned `CHAT_WIRE_API_REMOVED_ERROR`.

### 3. `claude-minimax-proxy.py` only exposed Chat Completions

The proxy routed:

- `POST /v1/messages` to MiniMax Anthropic-compatible endpoint
- `POST /v1/chat/completions` to MiniMax OpenAI-compatible chat endpoint
- `POST /v1/image_generation` to image endpoint

It had no `POST /v1/responses` handler, so even after fixing `wire_api`, Codex would receive `404` on every turn.

### 4. Stale `node_repl` runtime hash in `config.toml` (sidecar crash)

`[mcp_servers.node_repl]` and its `env` values were pointing to an old `cua_node` runtime directory (`f1bf3cd3a5929acd`) that no longer existed. When Codex started the in-app browser/REPL sidecar, the missing `node_repl.exe` caused the server to die with `Cannot call write after a stream was destroyed`.

**Fix:** Replace the stale hash with the currently installed runtime hash (`9ec47c3bbf131bc8`) everywhere it appears in the `node_repl` command and environment variables.

---

## Research summary

### Codex `wire_api`

- Source: `openai/codex/codex-rs/model-provider-info/src/lib.rs`
- `WireApi` enum only contains `Responses`.
- `wire_api = "chat"` now produces:  
  `'wire_api = "chat"' is no longer supported. How to fix: set 'wire_api = "responses"' in your provider config.`

### OpenAI Responses API shape

- Endpoint: `POST /v1/responses`
- Request body:  
  - `model`  
  - `input` — either a string or an array of message-like items  
  - optional `max_tokens`, `temperature`, `top_p`, `tools`, etc.
- Response:  
  - `id`, `object: "response"`, `created_at`, `model`  
  - `output[]` array containing `message` items with `content[]` of `output_text`  
  - `usage` with `input_tokens`, `output_tokens`, `total_tokens`

### Translation approach

Codex requires `POST /v1/responses`, but MiniMax only exposes `POST /v1/chat/completions`.  
The clean fix is to implement a Responses-to-Chat-Completions shim inside the proxy, similar to `codex-relay`.

---

## Corrections applied

### `C:\Users\Admin\.codex\config.toml`

1. Removed the duplicate `[mcp_servers.hermes3d-locks.env]` sub-table.
2. Changed the MiniMax provider to use `wire_api = "responses"`.

Current valid block:

```toml
[model_providers.minimax_gateway]
name = 'MiniMax via local Claude gateway'
base_url = 'http://127.0.0.1:48217/v1'
wire_api = 'responses'

[model_providers.minimax_gateway.auth]
command = 'powershell'
args = ['-NoProfile', '-Command', "Get-Content -LiteralPath 'G:/private/.proxy-token' -Raw"]
timeout_ms = 5000
refresh_interval_ms = 0
```

### `G:\Github\claude-codex-devin\claude-minimax-proxy.py`

1. Added `import secrets`.
2. Added `POST /v1/responses` route in `do_POST`.
3. Added `_call_openai_chat_sync()` to call MiniMax `POST /v1/chat/completions` synchronously.
4. Added `_proxy_responses()` to:
   - Read the Responses API request.
   - Validate the model against the bearer allowlist.
   - Translate `input` (string or array) to `messages`.
   - Force `stream = false` so the single JSON response can be translated.
   - Call MiniMax chat completions.
   - Translate the chat-completion response into the OpenAI Responses API `output` format with `output_text` content and `usage`.

Proxy now supports:

- `GET /v1/models`
- `POST /v1/messages`
- `POST /v1/chat/completions`
- `POST /v1/image_generation`
- `POST /v1/responses`

### Syntax validation

`python -m py_compile` on `claude-minimax-proxy.py` passed successfully.

---

## Correct end-to-end setup

### 1. Proxy token and key

Ensure these exist:

- `G:\private\.env` with `MINIMAX_API_KEY=...`
- `G:\private\.proxy-token` with a 64-hex shared token

### 2. Run the repair script

`G:\Github\claude-codex-devin\scripts\Repair-MinimaxGateway.ps1` will:

- Regenerate the proxy token if needed.
- Fix ACLs on the token and `.env` files.
- Update Claude Desktop registry for the Anthropic gateway (`http://127.0.0.1:48217/anthropic`).
- Restart `claude-minimax-proxy.py`.
- Smoke-test the proxy.

### 3. Codex `config.toml`

Minimum user-level `~/.codex/config.toml` provider block:

```toml
model = 'MiniMax-M3'
model_provider = 'minimax_gateway'

[model_providers.minimax_gateway]
name = 'MiniMax via local Claude gateway'
base_url = 'http://127.0.0.1:48217/v1'
wire_api = 'responses'

[model_providers.minimax_gateway.auth]
command = 'powershell'
args = ['-NoProfile', '-Command', "Get-Content -LiteralPath 'G:/private/.proxy-token' -Raw"]
timeout_ms = 5000
refresh_interval_ms = 0
```

**Important:** `wire_api` must be `'responses'`. `'chat'` causes `config_load` to fail.

### 4. ChatGPT desktop setup

When the `Finish Windows setup` / UAC prompt appears:

1. Click **Yes** in the UAC prompt.
2. Click **Try Windows setup again**.
3. If `config_load` still appears, the `config.toml` is still invalid or the proxy is not running.

### 5. Test the gateway

From PowerShell:

```powershell
$token = Get-Content 'G:/private/.proxy-token' -Raw
$body = @{ model = 'MiniMax-M3'; input = 'Say hello' } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri 'http://127.0.0.1:48217/v1/responses' -Method POST -Headers @{ 'X-Proxy-Token' = $token; 'Content-Type' = 'application/json' } -Body $body
```

A successful hit returns an `output` array with a `message` item and `output_text` content.

---

## Files changed

- `C:\Users\Admin\.codex\config.toml` — removed duplicate `env` table; `wire_api = 'responses'`; fixed stale `node_repl` runtime hash.
- `G:\Github\claude-codex-devin\claude-minimax-proxy.py` — added `POST /v1/responses` translator.
- `G:\Github\claude-codex-devin\docs\Codex-Setup-Audit.md` — this document.

## Known limitations

- Streaming `POST /v1/responses` is not supported yet. The proxy forces `stream = false` to the upstream and returns a single JSON response.
- Tool calls and reasoning items in the Responses API are not translated; only text `output_text` is returned.
- Full multimodal / vision / image / speech use still uses the existing `POST /v1/messages`, `POST /v1/chat/completions` and `POST /v1/image_generation` paths.

## References

- OpenAI Codex: Deprecating `chat/completions` support — `https://github.com/openai/codex/discussions/7782`
- OpenAI Codex `model-provider-info/src/lib.rs` — `https://github.com/openai/codex/blob/main/codex-rs/model-provider-info/src/lib.rs`
- OpenAI Responses API Reference — `https://developers.openai.com/api/reference/resources/responses/`
- OpenAI Migrate to Responses API — `https://developers.openai.com/api/docs/guides/migrate-to-responses`
