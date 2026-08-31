"""Bounded, authenticated, stateless Codex gateway. Request driven; no watchdog."""

import asyncio
import json
import os
from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from gateway_common import (
    MAX_BODY_BYTES,
    MAX_RESPONSE_BYTES,
    MAX_REQUESTS,
    BODY_TIMEOUT,
    UPSTREAM_TIMEOUT,
    REQUEST_DEADLINE,
    authorized,
    parse_dotenv,
    install_process_limits,
    strict_json,
)
from responses_bridge import build_chat_request, chat_response_to_responses, ResponseStream, make_id

__version__ = "0.2.0-rc1"
UPSTREAM_BASE_URL = os.environ.get("UPSTREAM_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
if UPSTREAM_BASE_URL not in ("https://api.minimax.io/v1", "https://api.minimaxi.com/v1"):
    raise ValueError("UPSTREAM_BASE_URL must be an approved MiniMax HTTPS endpoint")
UPSTREAM_API_KEY = os.environ.get("UPSTREAM_API_KEY", "")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "MiniMax-M3")
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "48218"))
app = FastAPI(title="MiniMax Responses gateway", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)


def upstream_key():
    if UPSTREAM_API_KEY:
        return UPSTREAM_API_KEY
    if os.environ.get("MINIMAX_API_KEY"):
        return os.environ["MINIMAX_API_KEY"]
    try:
        text = Path(os.environ.get("MINIMAX_ENV_FILE", r"C:\private\.env")).read_text(encoding="utf-8-sig")
        return parse_dotenv(text).get("MINIMAX_API_KEY", "")
    except (OSError, UnicodeError):
        return ""


def client_factory():
    return httpx.AsyncClient(
        timeout=httpx.Timeout(UPSTREAM_TIMEOUT, connect=10), follow_redirects=False, trust_env=False
    )


class RequestLimit:
    def __init__(self, app):
        self.app, self.active = app, 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if self.active >= MAX_REQUESTS:
            return await JSONResponse({"error": "gateway is busy"}, status_code=503, headers={"Retry-After": "2"})(
                scope, receive, send
            )
        self.active += 1
        try:
            await self.app(scope, receive, send)
        finally:
            self.active -= 1


app.add_middleware(RequestLimit)


async def bounded_read(response):
    data = bytearray()
    async for chunk in response.aiter_bytes():
        if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
            raise ValueError("upstream response exceeds limit")
        data.extend(chunk)
    return bytes(data)


async def sse_data(response):
    buffer, total, event_lines = b"", 0, []
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ValueError("stream exceeds limit")
        buffer += chunk
        if len(buffer) > 1024 * 1024:
            raise ValueError("SSE line exceeds limit")
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line = line.rstrip(b"\r")
            if line.startswith(b"data:"):
                event_lines.append(line[5:].lstrip(b" "))
            elif not line and event_lines:
                yield b"\n".join(event_lines).decode("utf-8")
                event_lines.clear()
    if buffer or event_lines:
        raise ValueError("incomplete SSE event")


async def stream_chat_to_responses(chat_req, model, resp_id, custom=()):
    state = ResponseStream(model, resp_id, custom)
    for event in state.begin():
        yield event
    try:
        async with asyncio.timeout(REQUEST_DEADLINE):
            async with client_factory() as client:
                async with client.stream(
                    "POST",
                    UPSTREAM_BASE_URL + "/chat/completions",
                    json=chat_req,
                    headers={"Authorization": "Bearer " + upstream_key()},
                ) as response:
                    if response.status_code != 200:
                        yield state.fail(f"MiniMax returned HTTP {response.status_code}")
                        return
                    async for data in sse_data(response):
                        if data == "[DONE]":
                            break
                        for event in state.accept(json.loads(data)):
                            yield event
                    for event in state.finish():
                        yield event
    except asyncio.CancelledError:
        raise  # Client disconnect closes upstream; never retry or restart.
    except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        yield state.fail()


@app.post("/v1/responses")
async def handle_responses(request: Request):
    if not authorized(request.headers):
        return JSONResponse({"error": "missing or invalid gateway token"}, status_code=401)
    if not upstream_key():
        return JSONResponse({"error": "upstream credential unavailable"}, status_code=503)
    try:
        body_bytes = bytearray()
        async with asyncio.timeout(BODY_TIMEOUT):
            async for chunk in request.stream():
                if len(body_bytes) + len(chunk) > MAX_BODY_BYTES:
                    return JSONResponse({"error": "request exceeds 8 MiB"}, status_code=413)
                body_bytes.extend(chunk)
        body = strict_json(body_bytes)
        chat_req, custom = build_chat_request(body, DEFAULT_MODEL)
    except TimeoutError:
        return JSONResponse({"error": "request body timeout"}, status_code=408)
    except (ValueError, UnicodeError, TypeError, AttributeError, RecursionError):
        return JSONResponse(
            {"error": "invalid or unsupported request; gateway requires stateless input and client-side tools"},
            status_code=400,
        )
    model, resp_id = chat_req["model"], make_id()
    if chat_req["stream"]:
        return StreamingResponse(
            stream_chat_to_responses(chat_req, model, resp_id, custom),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Request-Id": resp_id},
        )
    try:
        async with asyncio.timeout(REQUEST_DEADLINE):
            async with client_factory() as client:
                async with client.stream(
                    "POST",
                    UPSTREAM_BASE_URL + "/chat/completions",
                    json=chat_req,
                    headers={"Authorization": "Bearer " + upstream_key()},
                ) as response:
                    data = await bounded_read(response)
                    if response.status_code != 200:
                        status = response.status_code if 400 <= response.status_code <= 599 else 502
                        return JSONResponse(
                            {"error": {"message": "MiniMax rejected the request", "status": status}}, status_code=status
                        )
                    result = chat_response_to_responses(json.loads(data), model, resp_id, custom)
                    return JSONResponse(result)
    except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return JSONResponse({"error": "upstream request failed or returned an invalid response"}, status_code=502)


@app.get("/v1/models")
async def list_models():
    # Local advertised configuration; no speculative upstream calls.
    names = list(dict.fromkeys([DEFAULT_MODEL, "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"]))
    return {"object": "list", "data": [{"id": name, "object": "model", "owned_by": "minimax"} for name in names]}


@app.get("/health")
async def health():
    # Optional passive status endpoint; nothing invokes this on a schedule.
    return {"status": "ok", "version": __version__}


if __name__ == "__main__":
    import uvicorn

    install_process_limits()
    uvicorn.run(
        app, host=HOST, port=PORT, workers=1, access_log=False, limit_concurrency=MAX_REQUESTS + 2, timeout_keep_alive=5
    )
