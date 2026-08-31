"""Fault and allocation regressions using local fake upstreams only."""

import gc
import json
from pathlib import Path
import socket
import sys
import threading
import time
import tracemalloc
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gateway_contracts import ProxyContracts, FakeUpstream, ApiContracts


class FaultContracts(ProxyContracts):
    def test_context_suffix_used_by_desktop_titles_maps_to_m3(self):
        self.assertEqual(self.request({"model": "claude-sonnet-4-5[1m]", "messages": []})[0], 200)
        self.assertEqual(FakeUpstream.requests[-1][0]["model"], "MiniMax-M3")

    def test_non_finite_json_is_rejected(self):
        self.assertEqual(self.request({"temperature": float("nan")})[0], 400)

    def test_invalid_media_types_do_not_crash_handler(self):
        for body, path in (
            ({"model": []}, "/v1/images/generations"),
            ({"input": "test", "voice": {}}, "/v1/audio/speech"),
            ({"input": "test", "speed": "invalid"}, "/v1/audio/speech"),
        ):
            self.assertEqual(self.request(body, path=path)[0], 400)

    def test_header_drip_has_a_wall_deadline(self):
        from test_gateway_contracts import proxy, running

        with patch.object(proxy, "BODY_TIMEOUT", 0.15):
            server = proxy.BoundedHTTPServer(("127.0.0.1", 0), proxy.Handler)
            with running(server) as port:
                with socket.create_connection(("127.0.0.1", port), timeout=1) as sock:
                    sock.sendall(b"POST /v1/messages HTTP/1.0\r\n")
                    started = time.monotonic()
                    data = sock.recv(1024)
                    self.assertLess(time.monotonic() - started, 0.8)
                    self.assertNotIn(b"200 OK", data)

    def test_credentials_are_not_sent_to_redirect_destination(self):
        from test_gateway_contracts import proxy, running
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        destinations = []

        class Redirect(BaseHTTPRequestHandler):
            def do_POST(handler):
                destinations.append(handler.path)
                handler.send_response(307)
                handler.send_header("Location", f"http://127.0.0.1:{port}/steal-key")
                handler.end_headers()

            def log_message(handler, *args):
                pass

        with running(ThreadingHTTPServer(("127.0.0.1", 0), Redirect)) as port:
            with patch.object(proxy, "TARGET_BASE", f"http://127.0.0.1:{port}"):
                self.assertEqual(self.request()[0], 502)
                self.assertEqual(destinations, ["/v1/messages"])

    def test_repeated_requests_release_threads_and_python_allocations(self):
        for _ in range(25):
            self.assertEqual(self.request()[0], 200)
        FakeUpstream.requests.clear()  # The fixture intentionally records requests.
        gc.collect()
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        threads = threading.active_count()
        for _ in range(300):
            self.assertEqual(self.request()[0], 200)
            FakeUpstream.requests.clear()
        gc.collect()
        retained = tracemalloc.get_traced_memory()[0] - baseline
        tracemalloc.stop()
        self.assertLess(retained, 2 * 1024 * 1024)
        # Timer threads can still be completing their cancellation when measured.
        self.assertLessEqual(threading.active_count(), threads + 4)
        print(
            json.dumps(
                {
                    "soak_requests": 325,
                    "retained_python_bytes": retained,
                    "thread_count_before": threads,
                    "thread_count_after": threading.active_count(),
                }
            )
        )


class UpstreamFaultContracts(ApiContracts):
    def test_invalid_upstream_shapes_return_502(self):
        for shape in (
            {"choices": [None]},
            {"choices": [{"finish_reason": "stop", "message": None}]},
            {"choices": [{"finish_reason": "stop", "message": {"tool_calls": [None]}}]},
        ):
            self.upstream(lambda req: self.httpx.Response(200, json=shape))
            result = self.client.post("/v1/responses", headers=self.headers, json={"input": "hi"})
            self.assertEqual(result.status_code, 502)


def load_tests(loader, tests, pattern):
    # Run only the new contracts here. Baseline contracts are discovered in
    # test_gateway_contracts, so a count cannot be inflated by imported classes.
    suite = unittest.TestSuite()
    for cls in (FaultContracts, UpstreamFaultContracts):
        for name in cls.__dict__:
            if name.startswith("test_"):
                suite.addTest(cls(name))
    return suite


if __name__ == "__main__":
    unittest.main()
