"""Network contracts against local fake upstreams. No real keys or paid calls."""

import contextlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("proxy_contract", ROOT / "claude-minimax-proxy.py")
proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy)
from gateway_common import MAX_BODY_BYTES, MAX_REQUESTS
from responses_bridge import build_chat_request, chat_response_to_responses, ResponseStream


@contextlib.contextmanager
def running(server):
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


class FakeUpstream(BaseHTTPRequestHandler):
    requests = []
    release = threading.Event()

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((body, dict(self.headers)))
        if body.get("system") == "reject":
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error":"rate limited"}')
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if body.get("stream") else "application/json")
        self.end_headers()
        if body.get("stream"):
            self.wfile.write(b'event: message_start\ndata: {"type":"message_start"}\n\n')
            self.wfile.flush()
            type(self).release.wait(3)
            try:
                self.wfile.write(b'event: message_stop\ndata: {"type":"message_stop"}\n\n')
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.wfile.write(
                json.dumps(
                    {"model": body["model"], "tools": body.get("tools"), "max_tokens": body.get("max_tokens")}
                ).encode()
            )


class ProxyContracts(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            patch.dict(os.environ, {"MINIMAX_PROXY_TOKEN": "test-token-" * 4, "MINIMAX_API_KEY": "fake-upstream-key"})
        )
        FakeUpstream.requests = []
        FakeUpstream.release.clear()
        self.addCleanup(FakeUpstream.release.set)
        upstream = self.stack.enter_context(running(ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)))
        self.stack.enter_context(patch.object(proxy, "TARGET_BASE", f"http://127.0.0.1:{upstream}"))
        self.port = self.stack.enter_context(running(proxy.BoundedHTTPServer(("127.0.0.1", 0), proxy.Handler)))

    def request(self, body=None, path="/anthropic/v1/messages", token="test-token-" * 4, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        headers = {"Content-Type": "application/json", "X-Api-Key": token}
        data = (
            raw
            if raw is not None
            else json.dumps(
                body if body is not None else {"model": "claude-sonnet-4-5", "max_tokens": 64, "messages": []}
            ).encode()
        )
        conn.request("POST", path, body=data, headers=headers)
        result = conn.getresponse()
        status, content = result.status, result.read()
        conn.close()
        return status, content

    def test_authentication_rejects_grok_placeholders(self):
        for token in ("", "proxy-managed", "sk-proxy", "local"):
            self.assertEqual(self.request(token=token)[0], 401)
        self.assertFalse(FakeUpstream.requests)

    def test_missing_token_fails_closed_even_with_old_escape_hatch(self):
        with patch.dict(
            os.environ,
            {
                "MINIMAX_PROXY_TOKEN": "",
                "MINIMAX_PROXY_TOKEN_FILE": str(ROOT / "missing-token"),
                "MINIMAX_PROXY_TOKEN_DISABLED": "1",
            },
        ):
            self.assertEqual(self.request()[0], 401)

    def test_invalid_bodies_are_errors_not_crashes(self):
        for raw in (b"[]", b"null", b"bad", b"\xff", b'{"stream":"yes"}'):
            self.assertEqual(self.request(raw=raw)[0], 400)
        self.assertFalse(FakeUpstream.requests)

    def test_negative_duplicate_and_oversize_lengths_are_rejected(self):
        for length, extra, expected in (
            ("-1", "", 400),
            (str(MAX_BODY_BYTES + 1), "", 413),
            ("2", "Content-Length: 2\r\n", 400),
        ):
            with socket.create_connection(("127.0.0.1", self.port), timeout=2) as sock:
                request = (
                    f"POST /v1/messages HTTP/1.0\r\nX-Api-Key: {'test-token-' * 4}\r\n"
                    f"Content-Length: {length}\r\n{extra}\r\n"
                )
                sock.sendall(request.encode())
                self.assertIn(str(expected).encode(), sock.recv(1024).split(b"\r\n")[0])

    def test_requests_never_replay_a_cached_tool_result(self):
        for maximum, tools in ((8, []), (96, [{"name": "write_file", "input_schema": {"type": "object"}}]), (96, [])):
            status, data = self.request(
                {"model": "claude-opus-4-6", "max_tokens": maximum, "tools": tools, "messages": []}
            )
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data)["max_tokens"], maximum)
            self.assertEqual(json.loads(data)["tools"], tools)
        self.assertEqual(len(FakeUpstream.requests), 3)
        self.assertEqual(FakeUpstream.requests[0][0]["model"], "MiniMax-M2.7")
        self.assertEqual(
            {k.lower(): v for k, v in FakeUpstream.requests[0][1].items()}["x-api-key"], "fake-upstream-key"
        )

    def test_direct_model_is_preserved_and_unknown_is_rejected(self):
        self.assertEqual(self.request({"model": "MiniMax-M2.7-highspeed", "messages": []})[0], 200)
        self.assertEqual(FakeUpstream.requests[-1][0]["model"], "MiniMax-M2.7-highspeed")
        for model in ("internal-model", ["bad"]):
            self.assertEqual(self.request({"model": model})[0], 400)

    def test_stream_first_event_arrives_before_upstream_finishes(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1)
        self.addCleanup(conn.close)
        conn.request(
            "POST",
            "/v1/messages",
            json.dumps({"model": "claude-sonnet-4-5", "stream": True}),
            {"X-Api-Key": "test-token-" * 4, "Content-Type": "application/json"},
        )
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.readline(), b"event: message_start\n")
        self.assertFalse(FakeUpstream.release.is_set())
        FakeUpstream.release.set()
        self.assertIn(b"message_stop", response.read())

    def test_upstream_error_keeps_http_status_and_is_not_retried(self):
        status, data = self.request({"model": "claude-sonnet-4-5", "system": "reject"})
        self.assertEqual(status, 429)
        self.assertEqual(len(FakeUpstream.requests), 1)
        self.assertNotIn(b"HTTP/", data)

    def test_ready_before_first_paid_call(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/readyz")
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        response.read()
        conn.close()
        self.assertFalse(FakeUpstream.requests)

    def test_admission_limit_refuses_overload(self):
        # Claim all slots deterministically; overload must not create another handler.
        server = proxy.BoundedHTTPServer(("127.0.0.1", 0), proxy.Handler)
        with running(server) as port:
            for _ in range(MAX_REQUESTS):
                self.assertTrue(server.slots.acquire(False))
            try:
                # Exercise the accept/read race on Windows, including a body
                # that must not reset the connection before 503 is received.
                for _ in range(25):
                    for method, body in [("GET", None), ("POST", b"x" * 8192)]:
                        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                        try:
                            conn.request(method, "/healthz", body=body)
                            response = conn.getresponse()
                            self.assertEqual(response.status, 503)
                            response.read()
                        finally:
                            conn.close()
            finally:
                for _ in range(MAX_REQUESTS):
                    server.slots.release()
            self.assertFalse(FakeUpstream.requests)


def decode_events(events):
    return [json.loads(event.split("data: ", 1)[1]) for event in events]


class ResponsesContracts(unittest.TestCase):
    def test_function_call_is_top_level_and_survives_round_trip(self):
        upstream = {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {"id": "call_1", "function": {"name": "read_file", "arguments": '{"path":"x"}'}}
                        ],
                    },
                }
            ]
        }
        response = chat_response_to_responses(upstream, "MiniMax-M3", "resp_test")
        self.assertEqual(response["output"][0]["type"], "function_call")
        request, _ = build_chat_request(
            {
                "model": "MiniMax-M3",
                "input": response["output"]
                + [{"type": "function_call_output", "call_id": "call_1", "output": "file text"}],
            }
        )
        self.assertEqual(request["messages"][0]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(request["messages"][1], {"role": "tool", "tool_call_id": "call_1", "content": "file text"})

    def test_image_data_is_preserved(self):
        image = "data:image/png;base64,AA=="
        request, _ = build_chat_request(
            {
                "model": "MiniMax-M3",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Look"},
                            {"type": "input_image", "image_url": image},
                        ],
                    }
                ],
            }
        )
        self.assertEqual(request["messages"][0]["content"][1]["image_url"]["url"], image)

    def test_custom_tool_input_round_trip(self):
        request, custom = build_chat_request(
            {
                "model": "MiniMax-M3",
                "input": "edit",
                "tools": [{"type": "custom", "name": "apply_patch", "format": {"type": "text"}}],
            }
        )
        self.assertEqual(request["tools"][0]["function"]["parameters"]["required"], ["input"])
        response = chat_response_to_responses(
            {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call_x",
                                    "function": {"name": "apply_patch", "arguments": '{"input":"patch text"}'},
                                }
                            ]
                        },
                    }
                ]
            },
            "MiniMax-M3",
            "resp_x",
            custom,
        )
        self.assertEqual(response["output"][0]["input"], "patch text")
        self.assertEqual(response["output"][0]["type"], "custom_tool_call")

    def test_tool_policy_and_budget_are_forwarded(self):
        request, _ = build_chat_request(
            {
                "model": "MiniMax-M3",
                "input": "x",
                "max_output_tokens": 123,
                "parallel_tool_calls": False,
                "tool_choice": {"type": "function", "name": "f"},
            }
        )
        self.assertEqual(request["max_tokens"], 123)
        self.assertFalse(request["parallel_tool_calls"])
        self.assertEqual(request["tool_choice"]["function"]["name"], "f")

    def test_unsupported_features_fail_explicitly(self):
        for extra in (
            {"background": True},
            {"previous_response_id": "old"},
            {"tools": [{"type": "web_search"}]},
            {"input": 9},
        ):
            with self.assertRaises(ValueError):
                build_chat_request({"model": "MiniMax-M3", "input": "x", **extra})

    def test_legitimate_text_is_not_deleted_by_reasoning_heuristic(self):
        text = "The user manual is here.\n\n思考 is a word."
        result = chat_response_to_responses(
            {"choices": [{"finish_reason": "stop", "message": {"content": text}}]}, "m", "r"
        )
        self.assertEqual(result["output"][0]["content"][0]["text"], text)

    def test_stream_argument_fragments_and_indices_match_final_output(self):
        state = ResponseStream("MiniMax-M3", "resp_test")
        events = state.begin()
        for chunk in [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {"index": 4, "id": "call_a", "function": {"name": "f", "arguments": '{"x":'}}
                            ]
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [{"index": 8, "id": "call_b", "function": {"name": "g", "arguments": "{}"}}]
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {"tool_calls": [{"index": 4, "function": {"arguments": "1}"}}]},
                        "finish_reason": "tool_calls",
                    }
                ]
            },
        ]:
            events.extend(state.accept(chunk))
        events.extend(state.finish())
        decoded = decode_events(events)
        self.assertEqual([e["sequence_number"] for e in decoded], list(range(len(decoded))))
        final = decoded[-1]["response"]["output"]
        self.assertEqual([i["call_id"] for i in final], ["call_a", "call_b"])
        self.assertEqual(final[0]["arguments"], '{"x":1}')
        args = "".join(
            e["delta"]
            for e in decoded
            if e["type"] == "response.function_call_arguments.delta" and e["output_index"] == 0
        )
        self.assertEqual(args, final[0]["arguments"])
        for event in decoded:
            if "output_index" in event:
                self.assertLess(event["output_index"], len(final))

    def test_truncated_stream_is_not_completed(self):
        state = ResponseStream("m", "r")
        state.accept({"choices": [{"delta": {"content": "partial"}}]})
        with self.assertRaises(ValueError):
            state.finish()
        self.assertEqual(decode_events([state.fail()])[0]["type"], "response.failed")

    def test_length_limit_is_reported_as_incomplete(self):
        state = ResponseStream("m", "r")
        state.accept({"choices": [{"delta": {"content": "partial"}, "finish_reason": "length"}]})
        final = decode_events(state.finish())[-1]
        self.assertEqual(final["type"], "response.incomplete")
        self.assertEqual(final["response"]["incomplete_details"]["reason"], "max_output_tokens")


class ApiContracts(unittest.TestCase):
    def setUp(self):
        import api2codex
        import httpx
        from fastapi.testclient import TestClient

        self.api, self.httpx = api2codex, httpx
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {"MINIMAX_PROXY_TOKEN": "test-token-" * 4}))
        self.stack.enter_context(patch.object(api2codex, "UPSTREAM_API_KEY", "fake-upstream"))
        self.client = self.stack.enter_context(TestClient(api2codex.app))
        self.headers = {"Authorization": "Bearer " + "test-token-" * 4}

    def upstream(self, handler):
        transport = self.httpx.MockTransport(handler)
        self.stack.enter_context(
            patch.object(self.api, "client_factory", lambda: self.httpx.AsyncClient(transport=transport))
        )

    def test_auth_and_invalid_json(self):
        self.assertEqual(self.client.post("/v1/responses", json={}).status_code, 401)
        for raw in ("[]", "null", "{", '{"input":9}'):
            self.assertEqual(self.client.post("/v1/responses", headers=self.headers, content=raw).status_code, 400)

    def test_upstream_status_is_preserved(self):
        self.upstream(lambda req: self.httpx.Response(429, text="rate limited"))
        response = self.client.post("/v1/responses", headers=self.headers, json={"input": "hi"})
        self.assertEqual(response.status_code, 429)

    def test_transport_error_is_502(self):
        def fail(req):
            raise self.httpx.ConnectError("offline", request=req)

        self.upstream(fail)
        self.assertEqual(self.client.post("/v1/responses", headers=self.headers, json={"input": "hi"}).status_code, 502)

    def test_interrupted_upstream_emits_failed_not_completed(self):
        self.upstream(
            lambda req: self.httpx.Response(200, content=b'data:{"choices":[{"delta":{"content":"partial"}}]}\n\n')
        )
        result = self.client.post("/v1/responses", headers=self.headers, json={"input": "hi", "stream": True})
        self.assertIn("response.failed", result.text)
        self.assertNotIn("response.completed", result.text)

    def test_successful_stream_emits_completed(self):
        self.upstream(
            lambda req: self.httpx.Response(
                200,
                content=b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
            )
        )
        result = self.client.post("/v1/responses", headers=self.headers, json={"input": "hi", "stream": True})
        self.assertIn("response.completed", result.text)
        self.assertNotIn("response.failed", result.text)

    def test_body_limit(self):
        result = self.client.post("/v1/responses", headers=self.headers, content=b"x" * (MAX_BODY_BYTES + 1))
        self.assertEqual(result.status_code, 413)


if __name__ == "__main__":
    unittest.main(verbosity=2)
