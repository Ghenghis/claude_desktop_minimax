#!/usr/bin/env python3
"""Request-only MiniMax gateway for native Claude clients.

Tools remain in the client; this process only forwards authenticated HTTP.
Local gateway credentials are distinct from the upstream API credential.
"""

import json
import os
import sys
import time
import threading
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from gateway_common import (
    MAX_BODY_BYTES,
    MAX_RESPONSE_BYTES,
    MAX_REQUESTS,
    BODY_TIMEOUT,
    install_process_limits,
    open_upstream,
    strict_json,
)
from responses_bridge import TEXT_MODELS
from urllib.request import Request

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
    r"C:\private\.env",
]

# Model allowlist for multimodal endpoints (security Gap 3). The /v1/messages
# Anthropic-compat path uses pick_minimax_model() (picker-tier rewrite); the
# Bearer endpoints use this explicit allowlist. Anything else is rejected
# with 400 — including `MiniMax-M3-experimental` or any other *prefix* of a
# known model, which is the security hole a prefix-based allowlist would
# create (T1 in the security audit).
BEARER_MODEL_ALLOWLIST_EXACT = {
    # Chat models (MiniMax-M family)
    "MiniMax-M3",
    "MiniMax-M2.7",
    "MiniMax-M2.7-highspeed",
    "MiniMax-M2.5",
    "MiniMax-M2.5-highspeed",
    "MiniMax-M2.1",
    "MiniMax-M2.1-highspeed",
    "MiniMax-M2",
    "M2-her",
    # Video models
    "MiniMax-H3",
    "Hailuo-02",
    "Hailuo-2.3",
    "Hailuo-2.3Fast",
    "T2V-01-Director",
    "T2V-01",
    "I2V-01-Director",
    "I2V-01-live",
    "I2V-01",
    # Speech / TTS models
    "speech-2.8-hd",
    "speech-2.8-turbo",
    "speech-2.6-hd",
    "speech-2.6-turbo",
    "speech-02-hd",
    "speech-02-turbo",
    "speech-01-hd",
    "speech-01-turbo",
    # Music models
    "music-3.0",
    "music-2.6",
    "music-cover",
    "music-2.0",
    # Image model
    "image-01",
}


def _load_key_cached(force_reload=False):
    # Revocation takes effect on the next request; never reuse a removed secret.
    direct = os.environ.get("MINIMAX_API_KEY", "").strip()
    if direct:
        return direct
    candidates = [os.environ["MINIMAX_ENV_FILE"]] if os.environ.get("MINIMAX_ENV_FILE") else ENV_FILE_CANDIDATES
    for path in candidates:
        if not path:
            continue
        try:
            with open(path, encoding="utf-8-sig") as file:
                parsed = _parse_dotenv(file.read())
            key = parsed.get("MINIMAX_API_KEY") or parsed.get("MINIMAX_KEY")
            if key:
                return key
        except (OSError, UnicodeError):
            pass
    return None


def load_minimax_key():
    return _load_key_cached()


# Last successful upstream timestamp (set by _proxy_messages). Used by /readyz.
_last_upstream_ok_ts = {"value": 0.0}


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


# Map each Anthropic-looking picker slot to a distinct MiniMax model.
# The picker labels (Set-ClaudeDesktopGateway.ps1 labelOverride) promise:
#   sonnet -> MiniMax-M3, opus -> MiniMax-M2.7, haiku -> MiniMax-M2.7-highspeed
DEFAULT_MINIMAX_MODEL = "MiniMax-M3"
MODEL_MAP = {
    "claude-sonnet-4-5[1m]": "MiniMax-M3",
    "claude-sonnet-4[1m]": "MiniMax-M3",
    "claude-sonnet-4-5": "MiniMax-M3",
    "claude-sonnet-4": "MiniMax-M3",
    "claude-3-5-sonnet-20241022": "MiniMax-M3",
    "claude-3-5-sonnet": "MiniMax-M3",
    "claude-opus-4-6": "MiniMax-M2.7",
    "claude-opus-4": "MiniMax-M2.7",
    "claude-haiku-4-5": "MiniMax-M2.7-highspeed",
    "claude-haiku-4": "MiniMax-M2.7-highspeed",
}


def _load_proxy_token(force_reload=False):
    from gateway_common import private_token

    return private_token()


def _is_bearer_model_allowed(name):
    """Return True if `name` is in the multimodal allowlist (security Gap 3).
    Exact-match only. No prefix matching — that's the T1 vulnerability.
    """
    return isinstance(name, str) and name in TEXT_MODELS


class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = MAX_REQUESTS
    allow_reuse_address = False

    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(MAX_REQUESTS)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            try:
                request.settimeout(0.2)
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nRetry-After: 2\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(BODY_TIMEOUT)
        self._headers_sent = False
        self._request_body = None
        # A drip-fed header/body cannot hold a request slot indefinitely.
        self._body_timer = threading.Timer(BODY_TIMEOUT, self._expire_body)
        self._body_timer.daemon = True
        self._body_timer.start()

    def _expire_body(self):
        try:
            self.connection.shutdown(socket.SHUT_RD)
        except OSError:
            pass

    def end_headers(self):
        self._body_timer.cancel()
        super().end_headers()
        self._headers_sent = True

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            # A disconnected client ends this request, never restarts the gateway.
            self.close_connection = True
        finally:
            self._body_timer.cancel()

    def log_message(self, fmt, *args):
        pass  # Do not persist prompts, URLs, or per-request access logs.

    def _send_json(self, code, obj):
        if self._headers_sent:
            self.close_connection = True
            return
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
            # Returns 200 only when (a) the .env key is loaded and the local token is available.
            # Upstream success is informational, never a reason to restart.
            key_ok = bool(_load_key_cached())
            upstream_ok = bool(_last_upstream_ok_ts["value"])
            body = {
                "key": key_ok,
                "upstream": upstream_ok,
                "last_ok_ts": _last_upstream_ok_ts["value"],
            }
            body["token"] = bool(_load_proxy_token())
            self._send_json(200 if (key_ok and body["token"]) else 503, body)
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
            path = path[len("/anthropic") :] or path

        # Everything else requires the shared-secret token (Gap 1).
        if not self._check_proxy_token():
            self._send_json(401, {"error": "missing or invalid X-Proxy-Token"})
            return

        body = self._read_body()
        if body is None:
            return
        try:
            payload = strict_json(body)
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            if "stream" in payload and not isinstance(payload["stream"], bool):
                raise ValueError("stream must be boolean")
        except (ValueError, UnicodeError, RecursionError):
            self._send_json(400, {"error": "body must be a JSON object with valid field types"})
            return
        if path == "/v1/messages/count_tokens":
            # Local estimate, not an upstream billing count. Never report zero.
            self._send_json(200, {"input_tokens": max(1, (len(body) + 2) // 3), "estimated": True})
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

        self._send_json(
            404,
            {
                "error": "MiniMax gateway does not support this path or feature",
                "provider": "minimax",
                "path": self.path,
            },
        )

    def _check_proxy_token(self):
        from gateway_common import authorized

        return authorized(self.headers)

    def _proxy_messages(self):
        payload = json.loads(self._request_body)
        original = payload.get("model", "")
        if not isinstance(original, str):
            self._send_json(400, {"error": "model must be a string"})
            return
        if original in MODEL_MAP:
            payload["model"] = MODEL_MAP[original]
        elif original in {
            "MiniMax-M3",
            "MiniMax-M2.7",
            "MiniMax-M2.7-highspeed",
            "MiniMax-M2.5",
            "MiniMax-M2.5-highspeed",
            "MiniMax-M2.1",
            "MiniMax-M2.1-highspeed",
            "MiniMax-M2",
            "M2-her",
        }:
            payload["model"] = original
        else:
            self._send_json(400, {"error": "unsupported model; choose a configured picker model"})
            return
        # No response caching or automatic POST retries: preserve tools and stream bytes.
        self._proxy_upstream(
            TARGET_BASE + "/v1/messages",
            json.dumps(payload).encode(),
            "x-api-key",
            ("Content-Type", "anthropic-version", "anthropic-beta", "Accept"),
        )

    def _read_body(self):
        if self._request_body is not None:
            return self._request_body
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
            self._send_json(400, {"error": "one Content-Length header is required; chunked uploads unsupported"})
            return None
        try:
            length = int(lengths[0])
        except ValueError:
            length = -1
        if length < 0:
            self._send_json(400, {"error": "invalid Content-Length"})
            return None
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "request exceeds 8 MiB"})
            return None
        try:
            body = self.rfile.read(length)
        except (TimeoutError, OSError):
            self._send_json(408, {"error": "request body timeout"})
            return None
        if len(body) != length:
            self._send_json(400, {"error": "incomplete request body"})
            return None
        self._body_timer.cancel()
        self._request_body = body
        return body

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
        if not isinstance(model, str) or model != "image-01":
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
        """Translate an OpenAI /v1/audio/speech POST into MiniMax T2A v2."""
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
        if isinstance(model, str) and model.startswith("speech-") and model in BEARER_MODEL_ALLOWLIST_EXACT:
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
        try:
            voice = payload.get("voice", "alloy")
            if not isinstance(voice, str):
                raise ValueError("voice must be a string")
            voice_id = voice_map.get(voice, voice)
            speed = float(payload.get("speed", 1.0))
            pitch = int(payload.get("pitch", 0))
            volume = float(payload.get("volume", 1.0))
            if not (0.5 <= speed <= 2 and -12 <= pitch <= 12 and 0.1 <= volume <= 10):
                raise ValueError("voice parameter out of range")
        except (TypeError, ValueError, OverflowError):
            self._send_json(400, {"error": "invalid voice or speech parameters"})
            return

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
            with open_upstream(req) as resp:
                if resp.status != 200:
                    self._send_json(
                        resp.status if 400 <= resp.status <= 599 else 502,
                        {"error": "MiniMax rejected the speech request"},
                    )
                    return
                raw = resp.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("speech response exceeds limit")
                result = json.loads(raw)
                if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
                    raise ValueError("invalid speech response")
        except (OSError, ValueError, TypeError):
            self._send_json(502, {"error": "MiniMax speech request failed"})
            return

        base_resp = result.get("base_resp", {})
        if not isinstance(base_resp, dict) or base_resp.get("status_code", 0) != 0:
            self._send_json(502, {"error": "MiniMax rejected the speech request"})
            return

        audio_hex = result.get("data", {}).get("audio", "")
        if not audio_hex:
            self._send_json(502, {"error": "MiniMax T2A returned no audio"})
            return
        try:
            audio_bytes = bytes.fromhex(audio_hex)
        except (ValueError, TypeError):
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

    def _proxy_responses(self):
        self._proxy_upstream(
            "http://127.0.0.1:48218/v1/responses",
            self._request_body,
            "bearer",
            ("Content-Type", "Accept"),
            local_bridge=True,
        )

    def _proxy_upstream(self, target_url, body, auth_style, forward_headers=(), local_bridge=False):
        key = _load_proxy_token() if local_bridge else load_minimax_key()
        if not key:
            self._send_json(503, {"error": "gateway credentials unavailable"})
            return
        req = Request(target_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        for header in forward_headers:
            value = self.headers.get(header)
            if value:
                req.add_header(header, value)
        req.add_header(
            "Authorization" if auth_style == "bearer" else "X-Api-Key",
            "Bearer " + key if auth_style == "bearer" else key,
        )
        try:
            with open_upstream(req) as resp:
                if not 200 <= resp.status < 300:
                    status = resp.status if 400 <= resp.status <= 599 else 502
                    self._send_json(
                        status,
                        {
                            "error": {
                                "type": "upstream_error",
                                "message": "Upstream rejected the request",
                                "status": status,
                            }
                        },
                    )
                    return
                self.send_response(resp.status)
                for header in ("Content-Type", "Content-Encoding", "Retry-After", "request-id"):
                    if resp.headers.get(header):
                        self.send_header(header, resp.headers[header])
                self.send_header("Connection", "close")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.close_connection = True
                total = 0
                while True:
                    chunk = resp.read1(8192)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise ValueError("upstream response limit exceeded")
                    self.wfile.write(chunk)
                    self.wfile.flush()
                if 200 <= resp.status < 300:
                    _last_upstream_ok_ts["value"] = time.time()
        except Exception:
            if not self._headers_sent:
                self._send_json(502, {"error": "upstream request failed or timed out"})
            else:
                # Never append a second HTTP status to a partially delivered SSE stream.
                self.close_connection = True


def main():
    install_process_limits()
    server = BoundedHTTPServer(("127.0.0.1", PORT), Handler)
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
