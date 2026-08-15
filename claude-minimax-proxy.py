#!/usr/bin/env python3
"""Local Claude Desktop <-> MiniMax model-renaming proxy.

Claude Desktop's third-party gateway mode rejects non-Anthropic model names in
inferenceModels (e.g. "MiniMax-M3"). This proxy lets Claude Desktop use an
Anthropic-looking model ID such as "claude-sonnet-4-5", then rewrites the
model field to "MiniMax-M3" before forwarding the request unchanged to
MiniMax's native Anthropic-compatible endpoint at https://api.minimax.io/anthropic.

It exposes:
    GET  /v1/models          (and /anthropic/v1/models)
    POST /v1/messages        (and /anthropic/v1/messages)

Configure Claude Desktop with:
    Gateway Base URL:    http://127.0.0.1:<PORT>/anthropic
    Gateway API Key:     <your MiniMax API key>
    Auth Scheme:         x-api-key
    inferenceModels:     [{"name":"claude-sonnet-4-5","anthropicFamilyTier":"sonnet","supports1m":true}]
"""

import json
import os
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PORT = int(os.environ.get("CLAUDE_MINIMAX_PROXY_PORT", "48217"))
# Anthropic-compatible chat (X-Api-Key)
TARGET_BASE = "https://api.minimax.io/anthropic"
# OpenAI-compatible + multimodal endpoints (Authorization: Bearer)
OPENAI_BASE = "https://api.minimax.io"

# Endpoints that take Authorization: Bearer rather than X-Api-Key.
# Anything routed to OPENAI_BASE uses Bearer; everything routed to TARGET_BASE
# uses X-Api-Key.
BEARER_PATH_PREFIXES = ("/v1/chat/completions",)

# Load the MiniMax API key from a .env-style file (KEY=VALUE, comments allowed).
# The key is held in process memory only and is never logged or echoed.
ENV_FILE_CANDIDATES = [
    os.environ.get("MINIMAX_ENV_FILE"),
    r"G:\private\.env",
    r"C:\private\.env",
    r"S:\private\.env",
    r"G:\Private\.env",
    r"C:\Private\.env",
]

# Shared-secret token file (security Gap 1, docs/admin-gateway-audit/06-bugs-and-polish.md).
# Claude Desktop sends `X-Proxy-Token: <value>` on every request; the proxy
# compares in constant time before forwarding. Token is 256-bit random hex,
# stored at mode 0600 in G:\private\.proxy-token alongside .env.
# Disable for development by setting MINIMAX_PROXY_TOKEN_DISABLED=1.
PROXY_TOKEN_CANDIDATES = [
    os.environ.get("MINIMAX_PROXY_TOKEN_FILE"),
    r"G:\private\.proxy-token",
    r"C:\private\.proxy-token",
    r"S:\private\.proxy-token",
]
PROXY_TOKEN_DISABLED = bool(os.environ.get("MINIMAX_PROXY_TOKEN_DISABLED"))

# Model allowlist for multimodal endpoints (security Gap 3). The /v1/messages
# Anthropic-compat path uses pick_minimax_model() (picker-tier rewrite); the
# Bearer endpoints use this explicit allowlist. Anything else is rejected
# with 400 — including `MiniMax-M3-experimental` or any other *prefix* of a
# known model, which is the security hole a prefix-based allowlist would
# create (T1 in the security audit).
BEARER_MODEL_ALLOWLIST_EXACT = {
    # Chat models (MiniMax-M family)
    "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed",
    "MiniMax-M2.5", "MiniMax-M2.5-highspeed",
    "MiniMax-M2.1", "MiniMax-M2.1-highspeed",
    "MiniMax-M2", "M2-her",
    # Video models
    "MiniMax-H3", "Hailuo-02", "Hailuo-2.3", "Hailuo-2.3Fast",
    "T2V-01-Director", "T2V-01",
    "I2V-01-Director", "I2V-01-live", "I2V-01",
    # Speech / TTS models
    "speech-2.8-hd", "speech-2.8-turbo",
    "speech-2.6-hd", "speech-2.6-turbo",
    "speech-02-hd", "speech-02-turbo",
    "speech-01-hd", "speech-01-turbo",
    # Music models
    "music-3.0", "music-2.6", "music-cover", "music-2.0",
    # Image model
    "image-01",
}

# In-memory cache for the MiniMax API key. Avoids re-parsing .env on every
# request and supports hot-reload via watchdog tick (P0 #5).
_key_cache = {"mtime_ns": 0, "key": None, "path": None}


def _load_key_cached(force_reload=False):
    """Return MiniMax key from cache; reload from disk only if .env mtime changed.

    Cache key is (path, mtime_ns). Once loaded, the value is held until the
    .env file's mtime changes (rotating the key no longer requires restart).
    """
    global _key_cache
    if PROXY_TOKEN_DISABLED and not _key_cache["key"]:
        # Allow the dev escape hatch: if the .env is unreachable, log once and
        # bail. This is the prod path; we never serve without a key.
        pass
    for path in ENV_FILE_CANDIDATES:
        if not path or not os.path.isfile(path):
            continue
        try:
            mtime_ns = os.stat(path).st_mtime_ns
        except OSError:
            continue
        if (
            not force_reload
            and _key_cache["path"] == path
            and _key_cache["mtime_ns"] == mtime_ns
            and _key_cache["key"]
        ):
            return _key_cache["key"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                parsed = _parse_dotenv(f.read())
        except OSError:
            continue
        key = parsed.get("MINIMAX_API_KEY") or parsed.get("MINIMAX_KEY")
        if key:
            _key_cache = {"mtime_ns": mtime_ns, "key": key, "path": path}
            return key
    return _key_cache["key"]  # may still be None on first call


# Backward-compatible shim — used by all upstream-call sites.
def load_minimax_key():
    return _load_key_cached()


# Last successful upstream timestamp (set by _proxy_messages). Used by /readyz.
_last_upstream_ok_ts = {"value": 0.0}

# SHA-256 exact-match cache (P0 #2 from the merge plan). Key is the
# canonicalized request body; value is the upstream response + headers.
# TTL configurable via MINIMAX_CACHE_TTL_SECONDS (default 24h).
import hashlib as _hashlib

CACHE_TTL_SECONDS = int(os.environ.get("MINIMAX_CACHE_TTL_SECONDS", "86400"))
CACHE_MAX_ENTRIES = int(os.environ.get("MINIMAX_CACHE_MAX_ENTRIES", "512"))
_cache = {"entries": {}}  # entries: {hash: {"body": bytes, "headers": list, "ts": float}}


def _compute_cache_key(model, payload):
    """SHA-256 over canonicalized (model, messages, temperature, system).

    Other fields (stream, max_tokens, tools) are excluded — those are
    call-shape choices that shouldn't break a cache hit when the user just
    wants a different length or stream mode.
    """
    canon = {
        "model": model,
        "messages": payload.get("messages", []),
        "system": payload.get("system", ""),
        "temperature": payload.get("temperature", 1.0),
    }
    blob = json.dumps(canon, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _hashlib.sha256(blob).hexdigest()


def _cache_get(key):
    """Return cached (body, headers) if present and fresh; else None."""
    entry = _cache["entries"].get(key)
    if not entry:
        return None
    age = time.time() - entry["ts"]
    if age > CACHE_TTL_SECONDS:
        _cache["entries"].pop(key, None)
        return None
    return entry["body"], entry["headers"]


def _cache_put(key, body, headers):
    """Store (body, headers) under key; evict oldest if at capacity."""
    entries = _cache["entries"]
    if len(entries) >= CACHE_MAX_ENTRIES:
        # Naive LRU: drop the oldest entry by ts.
        oldest_key = min(entries, key=lambda k: entries[k]["ts"])
        entries.pop(oldest_key, None)
    entries[key] = {"body": body, "headers": list(headers), "ts": time.time()}


def _parse_dotenv(text):
    """Parse a .env file into a dict without ever logging values.

    Supports `KEY=value`, optional double or single quotes, `#` comments,
    blank lines, and `export KEY=value`. Values are returned verbatim.
    """
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        # Skip empty values so MINIMAX_API_KEY="" fails loudly upstream rather
        # than silently returning an empty key (bug #16, 06-bugs-and-polish.md).
        if not value:
            continue
        out[key] = value
    return out


def load_minimax_key():
    """Return the MiniMax API key from the first readable .env candidate.

    The value is returned as a string and must never be written to logs,
    stderr, stdout, or disk. Treat it like a password at every callsite.
    """
    for path in ENV_FILE_CANDIDATES:
        if not path or not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                parsed = _parse_dotenv(f.read())
        except OSError:
            continue
        key = parsed.get("MINIMAX_API_KEY") or parsed.get("MINIMAX_KEY")
        if key:
            return key
    return None


# Map each Anthropic-looking picker slot to a distinct MiniMax model.
# sonnet  -> MiniMax-M3    (flagship, multimodal: text+image+video, 1M context)
# opus    -> MiniMax-M2.7  (text + tool calls only, no image/video input)
# haiku   -> MiniMax-M2.1  (text + tool calls only, no image/video input, faster)
DEFAULT_MINIMAX_MODEL = "MiniMax-M3"
MODEL_MAP = {
    "claude-sonnet-4-5": "MiniMax-M3",
    "claude-sonnet-4": "MiniMax-M3",
    "claude-3-5-sonnet-20241022": "MiniMax-M3",
    "claude-3-5-sonnet": "MiniMax-M3",
    "claude-opus-4-6": "MiniMax-M2.7",
    "claude-opus-4": "MiniMax-M2.7",
    "claude-haiku-4-5": "MiniMax-M2.1",
    "claude-haiku-4": "MiniMax-M2.1",
}


def pick_minimax_model(name):
    return MODEL_MAP.get(name, DEFAULT_MINIMAX_MODEL)


# Model Chains waterfall (P0 #4): when the primary model fails after retry
# exhaustion, try progressively cheaper/faster fallbacks. Each picker slot
# gets its own chain. Inspired by CCPG's "Model Chains" pattern.
MODEL_CHAINS = {
    # Sonnet -> try flagship first; on fail, fall to mid-tier; on fail, fall to fast.
    "claude-sonnet-4-5":       ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
    "claude-sonnet-4":         ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
    "claude-3-5-sonnet-20241022": ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
    "claude-3-5-sonnet":       ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
    # Opus -> M3 first (we use M2.7 normally but M3 wins on availability).
    "claude-opus-4-6":         ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
    "claude-opus-4":           ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
    # Haiku -> fast path; fall to even faster highspeed.
    "claude-haiku-4-5":        ["MiniMax-M2.1", "MiniMax-M2.7-highspeed"],
    "claude-haiku-4":          ["MiniMax-M2.1", "MiniMax-M2.7-highspeed"],
}


def chain_for(picker_model):
    """Return the ordered list of MiniMax models to try for `picker_model`.

    Defaults to a single-step chain through pick_minimax_model if the
    picker slot has no explicit chain (backward compat).
    """
    return MODEL_CHAINS.get(picker_model, [pick_minimax_model(picker_model)])


# --- Proxy-token loading (security Gap 1) ---
_token_cache = {"mtime_ns": 0, "value": None, "path": None}


def _load_proxy_token(force_reload=False):
    """Return the proxy token from the first readable candidate, cached by mtime."""
    global _token_cache
    for path in PROXY_TOKEN_CANDIDATES:
        if not path or not os.path.isfile(path):
            continue
        try:
            mtime_ns = os.stat(path).st_mtime_ns
        except OSError:
            continue
        if (
            not force_reload
            and _token_cache["path"] == path
            and _token_cache["mtime_ns"] == mtime_ns
            and _token_cache["value"]
        ):
            return _token_cache["value"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                tok = f.read().strip()
        except OSError:
            continue
        if tok:
            _token_cache = {"mtime_ns": mtime_ns, "value": tok, "path": path}
            return tok
    return _token_cache["value"]


def _is_bearer_model_allowed(name):
    """Return True if `name` is in the multimodal allowlist (security Gap 3).
    Exact-match only. No prefix matching — that's the T1 vulnerability.
    """
    if not name:
        return False
    return name in BEARER_MODEL_ALLOWLIST_EXACT


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s %s" % (self.log_date_time_string(), fmt % args), file=sys.stderr)

    def _send_json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Provider-Name", "minimax")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        # Security Gap 3: CORS is unnecessary (Claude Desktop is a native app,
        # not a browser) and the previous wildcard origin allowed any local
        # browser page to call our endpoints. Drop OPTIONS entirely.
        self._send_json(405, {"error": "OPTIONS not supported"})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            # Always 200 (cheap liveness probe). No upstream check.
            self._send_json(200, {"status": "ok"})
            return
        if path == "/readyz":
            # Returns 200 only when (a) the .env key is loaded and (b) we've
            # successfully talked to MiniMax at least once since startup.
            # Watchdog uses this to detect a hung-but-listening proxy.
            key_ok = bool(_load_key_cached())
            upstream_ok = bool(_last_upstream_ok_ts["value"])
            body = {
                "key": key_ok,
                "upstream": upstream_ok,
                "last_ok_ts": _last_upstream_ok_ts["value"],
            }
            self._send_json(200 if (key_ok and upstream_ok) else 503, body)
            return
        if path == "/anthropic/v1/models":
            # Anthropic-style list for Claude Desktop's discovery / picker.
            models = [
                {
                    "id": "claude-sonnet-4-5",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "minimax",
                    "anthropic_family_tier": "sonnet",
                    "is_family_default": True,
                },
                {
                    "id": "claude-opus-4-6",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "minimax",
                    "anthropic_family_tier": "opus",
                },
                {
                    "id": "claude-haiku-4-5",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "minimax",
                    "anthropic_family_tier": "haiku",
                },
            ]
            self._send_json(200, {"object": "list", "data": models})
            return
        if path == "/v1/models":
            # OpenAI-style list for Codex Desktop.
            minimax_models = [
                "MiniMax-M3",
                "MiniMax-M2.7",
                "MiniMax-M2.7-highspeed",
                "MiniMax-M2.5",
                "MiniMax-M2.5-highspeed",
                "MiniMax-M2.1",
                "MiniMax-M2.1-highspeed",
                "MiniMax-M2",
                "MiniMax-H3",
                "MiniMax-Hailuo-02",
            ]
            models = [
                {
                    "id": name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "minimax",
                }
                for name in minimax_models
            ]
            self._send_json(200, {"object": "list", "data": models})
            return
        self._send_json(404, {"error": "not found", "path": path})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        # Normalize /anthropic/v1/messages -> /v1/messages
        if path.startswith("/anthropic"):
            path = path[len("/anthropic"):] or path

        # Public, read-only endpoints that don't require the proxy token.
        if path == "/v1/messages/count_tokens":
            self._send_json(200, {"input_tokens": 0})
            return

        # Everything else requires the shared-secret token (Gap 1).
        if not self._check_proxy_token():
            self._send_json(401, {"error": "missing or invalid X-Proxy-Token"})
            return

        if path == "/v1/messages":
            self._proxy_messages()
            return
        if path == "/v1/chat/completions":
            self._proxy_openai_chat()
            return
        if path == "/v1/image_generation" or path == "/v1/images/generations":
            self._proxy_image_generation()
            return
        if path == "/v1/audio/speech":
            self._proxy_audio_speech()
            return
        if path == "/v1/responses":
            self._proxy_responses()
            return

        self._send_json(404, {"error": "MiniMax gateway does not support this path or feature", "provider": "minimax", "path": self.path})

    def _check_proxy_token(self):
        """Security Gap 1: validate the X-Proxy-Token header against the on-disk
        token. Constant-time compare. Returns True if valid OR if token auth is
        disabled via MINIMAX_PROXY_TOKEN_DISABLED (dev escape hatch only).
        """
        if PROXY_TOKEN_DISABLED:
            return True
        expected = _load_proxy_token()
        if not expected:
            # No token file present -- refuse to forward (fail closed).
            return False
        # Accept the shared token from any header a client can send. Claude
        # Desktop's stock third-party gateway config can only emit its API key
        # as X-Api-Key or Authorization: Bearer -- it has no way to send a
        # custom X-Proxy-Token header. Accept all three so the Gap 1
        # shared-secret check works with an unmodified Claude Desktop.
        provided = self.headers.get("X-Proxy-Token", "")
        if not provided:
            provided = self.headers.get("X-Api-Key", "")
        if not provided:
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                provided = auth[len("Bearer "):].strip()
        if not provided:
            return False
        # Constant-time compare; lengths should be identical (256-bit hex).
        if len(provided) != len(expected):
            return False
        result = 0
        for a, b in zip(provided.encode("utf-8"), expected.encode("utf-8")):
            result |= a ^ b
        return result == 0

    # --- Cache + retry helpers (P0 #2, P0 #3) ---

    def _write_cached_response(self, body_bytes, headers_list):
        """Write a previously-cached response back to the client."""
        # headers_list is the raw .headers.items() iteration order; replay as-is
        # minus hop-by-hop headers.
        skip = {"transfer-encoding", "content-length", "connection"}
        self.send_response(200)
        self.send_header("X-Cache", "HIT")
        for header, value in headers_list:
            if header.lower() not in skip:
                self.send_header(header, value)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _write_upstream_response(self, status, headers_list, body_bytes):
        """Write an upstream response back to the client.

        For streaming responses (no Content-Length), we wrap in chunked
        transfer encoding. For fixed-length responses, we pass through as-is.
        """
        skip = {"transfer-encoding", "content-length", "connection"}
        self.send_response(status)
        chunked = True
        for header, value in headers_list:
            if header.lower() == "content-length":
                chunked = False
                self.send_header(header, value)
            elif header.lower() not in skip:
                self.send_header(header, value)
        if chunked:
            self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        if chunked:
            offset = 0
            while offset < len(body_bytes):
                chunk = body_bytes[offset:offset + 8192]
                self.wfile.write(b"%X\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
                offset += len(chunk)
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        else:
            self.wfile.write(body_bytes)

    def _call_upstream_with_retry(self, req, label="upstream"):
        """Call urlopen with retry-on-5xx/429 + Retry-After respect (P0 #3).

        Returns (status, headers_list, body_bytes) on the final attempt (any
        status), or sends a 502 to the client and returns None if the request
        failed in an unrecoverable way (e.g. transport error after all retries).
        """
        from urllib.error import HTTPError, URLError
        import socket as _socket
        delays = [0.5, 2.0, 5.0]  # 3 attempts total
        last_error = None
        for attempt in range(3):
            try:
                with urlopen(req, timeout=180) as resp:
                    body = resp.read()
                    headers = list(resp.headers.items())
                    return resp.status, headers, body
            except HTTPError as e:
                last_error = e
                # Read body before deciding whether to retry.
                err_body = e.read()
                err_headers = list(e.headers.items())
                if e.code in (408, 425, 429, 500, 502, 503, 504) and attempt < 2:
                    sleep_for = delays[attempt]
                    # Honor Retry-After (capped at 30s).
                    for h, v in err_headers:
                        if h.lower() == "retry-after":
                            try:
                                sleep_for = min(float(v), 30.0)
                            except ValueError:
                                pass
                            break
                    print(f"[{label}] attempt {attempt + 1} got {e.code}; retrying in {sleep_for}s", file=sys.stderr)
                    time.sleep(sleep_for)
                    continue
                # Non-retryable; return the upstream error to the client.
                return e.code, err_headers, err_body
            except (URLError, _socket.timeout, OSError, ConnectionError) as e:
                last_error = e
                if attempt < 2:
                    print(f"[{label}] attempt {attempt + 1} transport error: {e}; retrying in {delays[attempt]}s", file=sys.stderr)
                    time.sleep(delays[attempt])
                    continue
                # Final transport error: send 502 to client.
                self._send_json(502, {"error": f"proxy error after {attempt + 1} attempts: {e}"})
                return None
        # Should not reach here.
        self._send_json(502, {"error": f"proxy error: {last_error}"})
        return None

    def _proxy_messages(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._send_json(400, {"error": "invalid Content-Length"})
            return
        # Body cap (bug #6 from 06-bugs-and-polish.md). 50 MB ceiling matches
        # what _read_body uses for Bearer endpoints.
        if content_length and content_length > 50 * 1024 * 1024:
            self._send_json(413, {"error": "body too large (>50MB)"})
            return
        body = self.rfile.read(content_length) if content_length else b""

        # Rewrite the model name in the request body.
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"invalid JSON: {e}"})
            return

        original_model = payload.get("model", "")
        # Bug #7: unknown model -> 400 instead of silent flagship fallback.
        if original_model and original_model not in MODEL_MAP:
            self._send_json(400, {"error": f"unsupported model: {original_model}"})
            return

        # SHA-256 exact-match cache (P0 #2). Cache key uses the picker
        # tier (not the resolved MiniMax model) so a hit returns the same
        # content regardless of which fallback served it.
        chain = chain_for(original_model)
        cache_key = _compute_cache_key(chain[0], {**payload, "model": chain[0]})
        cached = _cache_get(cache_key)
        if cached is not None:
            body_bytes, headers_list = cached
            self._write_cached_response(body_bytes, headers_list)
            return

        # Model Chains waterfall (P0 #4): try each model in order. Each
        # attempt gets the retry-with-backoff treatment internally.
        last_status = None
        last_headers = None
        last_body = None
        for idx, target_model in enumerate(chain):
            chain_payload = {**payload, "model": target_model}
            chain_body = json.dumps(chain_payload).encode("utf-8")

            req = Request(TARGET_BASE + "/v1/messages", data=chain_body, method="POST")
            for header in ("Content-Type", "anthropic-version", "Accept"):
                value = self.headers.get(header)
                if value:
                    req.add_header(header, value)
            key = load_minimax_key()
            if key:
                req.add_header("X-Api-Key", key)

            print(f"[chain] picker={original_model} attempt {idx + 1}/{len(chain)} model={target_model}", file=sys.stderr)
            response = self._call_upstream_with_retry(req, label=f"chain[{target_model}]")
            if response is None:
                return  # unrecoverable transport error, error already sent
            status, response_headers, response_body = response

            if 200 <= status < 300:
                _last_upstream_ok_ts["value"] = time.time()
                _cache_put(cache_key, response_body, response_headers)
                self._write_upstream_response(status, response_headers, response_body)
                return
            # Non-2xx: save and try next link in the chain.
            last_status = status
            last_headers = response_headers
            last_body = response_body
            print(f"[chain] model={target_model} returned {status}; falling through", file=sys.stderr)

        # All models in the chain failed.
        if last_status is not None:
            self._write_upstream_response(last_status, last_headers or [], last_body or b"")
        else:
            self._send_json(502, {"error": "all models in chain failed"})

    # --- Bearer-auth (OpenAI-compat + multimodal) endpoints ---

    def _read_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._send_json(400, {"error": "invalid Content-Length"})
            return None
        if content_length and content_length > 50 * 1024 * 1024:
            self._send_json(413, {"error": "body too large (>50MB)"})
            return None
        return self.rfile.read(content_length) if content_length else b""

    def _proxy_openai_chat(self):
        body = self._read_body()
        if body is None:
            return
        # Security Gap 3: enforce multimodal model allowlist.
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return
        model = payload.get("model", "")
        if not _is_bearer_model_allowed(model):
            self._send_json(400, {"error": f"unsupported model: {model}"})
            return
        body = json.dumps(payload).encode("utf-8")
        self._proxy_upstream(
            OPENAI_BASE + "/v1/chat/completions",
            body,
            auth_style="bearer",
            forward_headers=("Content-Type", "Accept"),
        )

    def _proxy_image_generation(self):
        body = self._read_body()
        if body is None:
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return
        # Gap 3: exact-match allowlist (no prefix matching — T1 vulnerability).
        model = payload.get("model", "")
        if model not in BEARER_MODEL_ALLOWLIST_EXACT:
            self._send_json(400, {"error": f"unsupported model: {model}"})
            return
        body = json.dumps(payload).encode("utf-8")
        self._proxy_upstream(
            OPENAI_BASE + "/v1/image_generation",
            body,
            auth_style="bearer",
            forward_headers=("Content-Type", "Accept"),
        )

    def _proxy_audio_speech(self):
        '''Translate an OpenAI /v1/audio/speech POST into MiniMax T2A v2.'''
        body = self._read_body()
        if body is None:
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return

        text = payload.get("input", "")
        if not text or not isinstance(text, str) or not text.strip():
            self._send_json(400, {"error": "input is required and must be a non-empty string"})
            return
        if len(text) > 10000:
            self._send_json(400, {"error": "input exceeds 10,000 characters"})
            return

        model = payload.get("model", "tts-1")
        if model in BEARER_MODEL_ALLOWLIST_EXACT:
            target_model = model
        elif model in ("tts-1", "tts-1-hd"):
            target_model = "speech-2.8-hd"
        else:
            self._send_json(400, {"error": f"unsupported TTS model: {model}"})
            return

        output_format = payload.get("response_format", "mp3")
        if output_format not in ("mp3", "wav", "flac"):
            self._send_json(400, {"error": f"unsupported response_format: {output_format}"})
            return

        voice_map = {
            "alloy": "English_Graceful_Lady",
            "echo": "English_Insightful_Speaker",
            "fable": "male-qn-qingse",
            "onyx": "male-qn-qingse",
            "nova": "English_Graceful_Lady",
            "shimmer": "English_Insightful_Speaker",
        }
        voice_id = voice_map.get(payload.get("voice", ""), "English_Graceful_Lady")
        speed = max(0.5, min(2.0, float(payload.get("speed", 1.0))))
        pitch = max(-12, min(12, int(payload.get("pitch", 0))))
        volume = max(0.1, min(10.0, float(payload.get("volume", 1.0))))

        t2a_payload = {
            "model": target_model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": speed,
                "vol": volume,
                "pitch": pitch,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": output_format,
                "channel": 1,
            },
            "output_format": "hex",
        }

        key = load_minimax_key()
        if not key:
            self._send_json(500, {"error": "MiniMax API key not configured"})
            return
        try:
            data = json.dumps(t2a_payload).encode("utf-8")
            req = Request(OPENAI_BASE + "/v1/t2a_v2", data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            req.add_header("Authorization", "Bearer " + key)
            with urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            err = e.read().decode("utf-8", "replace")
            self._send_json(e.code, {"error": f"MiniMax T2A error: {err}"})
            return
        except Exception as e:
            self._send_json(502, {"error": f"MiniMax T2A proxy error: {e}"})
            return

        base_resp = result.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            self._send_json(502, {
                "error": f"MiniMax T2A error [{base_resp.get('status_code')}]: {base_resp.get('status_msg')}"
            })
            return

        audio_hex = result.get("data", {}).get("audio", "")
        if not audio_hex:
            self._send_json(502, {"error": "MiniMax T2A returned no audio"})
            return
        try:
            audio_bytes = bytes.fromhex(audio_hex)
        except ValueError:
            self._send_json(502, {"error": "MiniMax T2A returned invalid audio data"})
            return

        content_type = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "flac": "audio/flac",
        }.get(output_format, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Provider-Name", "minimax")
        self.send_header("Content-Length", str(len(audio_bytes)))
        self.end_headers()
        self.wfile.write(audio_bytes)

    def _call_openai_chat_sync(self, payload):
        '''Call MiniMax /v1/chat/completions and return the parsed JSON.'''
        body = json.dumps(payload).encode('utf-8')
        key = load_minimax_key()
        if not key:
            raise RuntimeError('no MINIMAX_API_KEY available')
        req = Request(OPENAI_BASE + '/v1/chat/completions', data=body, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        req.add_header('Authorization', 'Bearer ' + key)
        with urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def _proxy_responses(self):
        '''Translate a Codex Responses API call into MiniMax chat/completions.'''
        body = self._read_body()
        if body is None:
            return
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json(400, {'error': 'invalid JSON'})
            return

        model = payload.get('model', '')
        if not _is_bearer_model_allowed(model):
            self._send_json(400, {'error': f'unsupported model: {model}'})
            return

        raw_input = payload.get('input')
        if isinstance(raw_input, str):
            messages = [{'role': 'user', 'content': raw_input}]
        elif isinstance(raw_input, list):
            messages = []
            for item in raw_input:
                if isinstance(item, dict) and 'role' in item and 'content' in item:
                    messages.append(item)
                elif isinstance(item, dict) and item.get('type') == 'message' and 'content' in item:
                    role = item.get('role', 'user')
                    content = item.get('content')
                    if isinstance(content, str):
                        messages.append({'role': role, 'content': content})
                    elif isinstance(content, list):
                        text = ' '.join(c.get('text', '') for c in content if isinstance(c, dict) and 'text' in c)
                        messages.append({'role': role, 'content': text})
                elif isinstance(item, dict) and 'text' in item:
                    messages.append({'role': 'user', 'content': item['text']})
                else:
                    self._send_json(400, {'error': 'unsupported input item'})
                    return
        else:
            self._send_json(400, {'error': 'input must be string or array'})
            return

        chat_payload = {
            'model': model,
            'messages': messages,
        }
        for key in ('max_tokens', 'temperature', 'top_p', 'stop', 'n', 'stream'):
            if key in payload:
                chat_payload[key] = payload[key]
        chat_payload['stream'] = False

        try:
            chat_resp = self._call_openai_chat_sync(chat_payload)
        except HTTPError as e:
            error_body = e.read() if hasattr(e, 'read') else b''
            self._send_json(e.code, {'error': error_body.decode('utf-8', 'replace')})
            return
        except Exception as e:
            self._send_json(502, {'error': f'proxy error: {e}'})
            return

        message = chat_resp.get('choices', [{}])[0].get('message', {})
        text = message.get('content', '') or ''
        chat_usage = chat_resp.get('usage', {})
        usage = {
            'input_tokens': chat_usage.get('prompt_tokens', 0),
            'output_tokens': chat_usage.get('completion_tokens', 0),
            'total_tokens': chat_usage.get('total_tokens', 0),
        }
        response = {
            'id': 'resp_' + secrets.token_hex(12),
            'object': 'response',
            'created_at': int(time.time()),
            'model': model,
            'output': [
                {
                    'id': 'msg_' + secrets.token_hex(12),
                    'type': 'message',
                    'role': 'assistant',
                    'status': 'completed',
                    'content': [
                        {
                            'type': 'output_text',
                            'text': text,
                            'annotations': []
                        }
                    ]
                }
            ],
            'usage': usage
        }
        self._send_json(200, response)

    def _proxy_upstream(self, target_url, body, auth_style, forward_headers=()):
        """Send `body` to `target_url`, inject the .env key in the requested
        auth style, and stream the response (SSE-friendly) back to the client.

        `forward_headers` is the tuple of client request headers to copy.
        Client-supplied Authorization / X-Api-Key are ALWAYS discarded.
        """
        key = load_minimax_key()
        if not key:
            self._send_json(502, {"error": "no MINIMAX_API_KEY available"})
            return

        req = Request(target_url, data=body, method="POST")
        for header in forward_headers:
            value = self.headers.get(header)
            if value:
                req.add_header(header, value)
        if auth_style == "bearer":
            req.add_header("Authorization", "Bearer " + key)
        else:
            req.add_header("X-Api-Key", key)

        client_had_auth = self.headers.get("Authorization") or self.headers.get("X-Api-Key")
        if client_had_auth:
            print(f"[key-path] client supplied auth header -- discarding and injecting MINIMAX_API_KEY from .env ({auth_style})", file=sys.stderr)
        else:
            print(f"[key-path] injected {auth_style} MINIMAX_API_KEY from .env (len={len(key)})", file=sys.stderr)

        try:
            with urlopen(req, timeout=180) as resp:
                self.send_response(resp.status)
                content_length = resp.headers.get("Content-Length")
                skip = {"transfer-encoding", "content-length", "connection"}
                for header, value in resp.headers.items():
                    if header.lower() not in skip:
                        self.send_header(header, value)
                if content_length:
                    self.send_header("Content-Length", content_length)
                    self.end_headers()
                    self.wfile.write(resp.read())
                else:
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(b"%X\r\n%s\r\n" % (len(chunk), chunk))
                        self.wfile.flush()
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
        except HTTPError as e:
            self.send_response(e.code)
            for header, value in e.headers.items():
                if header.lower() not in skip:
                    self.send_header(header, value)
            error_body = e.read()
            self.send_header("Content-Length", str(len(error_body)))
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            self._send_json(502, {"error": f"proxy error: {e}"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Claude<->MiniMax proxy listening on http://127.0.0.1:{PORT}/anthropic")
    print("Press Ctrl+C to stop.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", file=sys.stderr)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
