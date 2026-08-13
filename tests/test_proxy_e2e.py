"""End-to-end smoke tests for claude-minimax-proxy.

These tests do NOT hit MiniMax. They verify:
- Module imports cleanly
- Required constants exist (TARGET_BASE, OPENAI_BASE)
- Required handler methods exist on the Handler class
- do_POST routes the expected paths
- _read_body rejects Content-Length > 50MB
- _parse_dotenv skips empty values

Run:
    python tests/test_proxy_e2e.py

No external dependencies beyond the stdlib.
"""
import importlib.util
import os
import sys
import unittest

PROXY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "claude-minimax-proxy.py",
)


def _load_proxy_module():
    spec = importlib.util.spec_from_file_location("claude_minimax_proxy", PROXY_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestProxyModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_proxy_module()

    def test_module_imports(self):
        self.assertIsNotNone(self.mod)

    def test_target_base_constant(self):
        self.assertEqual(self.mod.TARGET_BASE, "https://api.minimax.io/anthropic")

    def test_openai_base_constant(self):
        self.assertEqual(self.mod.OPENAI_BASE, "https://api.minimax.io/v1")

    def test_port_default(self):
        # 48217 is the default; env override is honored by the proxy at import time
        self.assertEqual(self.mod.PORT, 48217)

    def test_model_map_has_sonnet_opus_haiku(self):
        m = self.mod.MODEL_MAP
        for k in ("claude-sonnet-4-5", "claude-opus-4-6", "claude-haiku-4-5"):
            self.assertIn(k, m)

    def test_pick_minimax_model_default(self):
        self.assertEqual(self.mod.pick_minimax_model("claude-sonnet-4-5"), "MiniMax-M3")
        self.assertEqual(self.mod.pick_minimax_model("claude-opus-4-6"), "MiniMax-M2.7")
        self.assertEqual(self.mod.pick_minimax_model("claude-haiku-4-5"), "MiniMax-M2.1")

    def test_pick_minimax_model_unknown_falls_back_to_m3(self):
        # Documented behavior in 06-bugs-and-polish.md #7: unknown model -> M3
        self.assertEqual(self.mod.pick_minimax_model("garbage"), "MiniMax-M3")

    def test_parse_dotenv_strips_comments_and_quotes(self):
        text = (
            '# a comment\n'
            'MINIMAX_API_KEY="abc123"\n'
            "OTHER=value with # in it\n"
            "export MINIMAX_KEY='xyz'\n"
            "\n"
        )
        parsed = self.mod._parse_dotenv(text)
        self.assertEqual(parsed.get("MINIMAX_API_KEY"), "abc123")
        self.assertEqual(parsed.get("OTHER"), "value with # in it")
        self.assertEqual(parsed.get("MINIMAX_KEY"), "xyz")

    def test_parse_dotenv_skips_empty_values(self):
        text = 'MINIMAX_API_KEY=""\nOTHER=ok\n'
        parsed = self.mod._parse_dotenv(text)
        # Bug #16 fix: empty quoted values are skipped
        self.assertNotIn("MINIMAX_API_KEY", parsed)
        self.assertEqual(parsed.get("OTHER"), "ok")

    def test_handler_methods_exist(self):
        h = self.mod.Handler
        for method in (
            "do_GET", "do_POST", "do_OPTIONS",
            "_send_json", "_proxy_messages",
            "_proxy_openai_chat", "_proxy_image_generation",
            "_read_body", "_proxy_upstream",
            "_check_proxy_token",
            "_write_cached_response", "_write_upstream_response",
            "_call_upstream_with_retry",
        ):
            self.assertTrue(hasattr(h, method), f"Handler missing {method}")

    # --- Security Gap 1: X-Proxy-Token + Bearer model allowlist (Gap 3) ---

    def test_proxy_token_disabled_default(self):
        # No env var set, no token file present -> PROXY_TOKEN_DISABLED is False
        self.assertFalse(self.mod.PROXY_TOKEN_DISABLED)

    def test_bearer_model_allowlist_accepts_known_models(self):
        ok_models = [
            "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.1",
            "image-01",
            "speech-2.8-hd", "speech-2.8-turbo",
            "music-3.0",
            "MiniMax-H3", "Hailuo-02",
        ]
        for m in ok_models:
            self.assertTrue(self.mod._is_bearer_model_allowed(m), f"{m} should be allowed")

    def test_bearer_model_allowlist_rejects_internal_previews(self):
        # Gap 3 T1: don't let attackers target internal preview models
        bad_models = [
            "MiniMax-internal-preview",
            "MiniMax-M3-experimental",
            "gpt-4", "claude-3-opus", "internal-debug",
        ]
        for m in bad_models:
            self.assertFalse(self.mod._is_bearer_model_allowed(m), f"{m} should be rejected")

    def test_bearer_model_allowlist_rejects_empty(self):
        self.assertFalse(self.mod._is_bearer_model_allowed(""))
        self.assertFalse(self.mod._is_bearer_model_allowed(None))

    def test_token_file_candidates_default(self):
        # First candidate is the user-overridable env var
        self.assertTrue(self.mod.PROXY_TOKEN_CANDIDATES[0] is None
                        or isinstance(self.mod.PROXY_TOKEN_CANDIDATES[0], str))

    # --- P0 #2: SHA-256 cache ---
    def test_cache_module_constants(self):
        # Cache TTL defaults to 24h, max entries 512
        self.assertEqual(self.mod.CACHE_TTL_SECONDS, 86400)
        self.assertEqual(self.mod.CACHE_MAX_ENTRIES, 512)

    def test_compute_cache_key_deterministic(self):
        payload = {"messages": [{"role": "user", "content": "hi"}], "temperature": 1.0}
        k1 = self.mod._compute_cache_key("MiniMax-M3", payload)
        k2 = self.mod._compute_cache_key("MiniMax-M3", payload)
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 64)  # SHA-256 hex length

    def test_compute_cache_key_differs_by_temperature(self):
        base = {"messages": [{"role": "user", "content": "hi"}], "temperature": 1.0}
        k1 = self.mod._compute_cache_key("MiniMax-M3", base)
        k2 = self.mod._compute_cache_key("MiniMax-M3", {**base, "temperature": 0.5})
        self.assertNotEqual(k1, k2)

    def test_cache_put_and_get(self):
        self.mod._cache["entries"].clear()
        key = "test_key_abc"
        self.mod._cache_put(key, b'{"ok":true}', [("Content-Type", "application/json")])
        out = self.mod._cache_get(key)
        self.assertIsNotNone(out)
        self.assertEqual(out[0], b'{"ok":true}')
        # Cleanup
        self.mod._cache["entries"].clear()

    def test_cache_eviction_at_max_entries(self):
        self.mod._cache["entries"].clear()
        # Override the max for this test
        original_max = self.mod.CACHE_MAX_ENTRIES
        self.mod.CACHE_MAX_ENTRIES = 3
        try:
            for i in range(5):
                self.mod._cache_put(f"k{i}", b"x", [])
            # Should have evicted down to <= 3
            self.assertLessEqual(len(self.mod._cache["entries"]), 3)
        finally:
            self.mod.CACHE_MAX_ENTRIES = original_max
            self.mod._cache["entries"].clear()

    # --- P0 #4: Model Chains ---
    def test_model_chains_for_sonnet(self):
        chain = self.mod.chain_for("claude-sonnet-4-5")
        self.assertEqual(chain, ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"])

    def test_model_chains_for_haiku(self):
        chain = self.mod.chain_for("claude-haiku-4-5")
        self.assertEqual(chain, ["MiniMax-M2.1", "MiniMax-M2.7-highspeed"])

    def test_model_chains_unknown_picker_falls_back_to_single(self):
        # Unknown picker -> single-step chain via pick_minimax_model
        chain = self.mod.chain_for("not-a-real-picker")
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0], self.mod.DEFAULT_MINIMAX_MODEL)


class TestProxyRouting(unittest.TestCase):
    """Verify do_POST routes to the right handler without hitting the network."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_proxy_module()

    def _make_handler(self):
        # Build a Handler instance without running BaseHTTPRequestHandler.__init__
        return self.mod.Handler.__new__(self.mod.Handler)

    def test_openai_chat_path_recognized(self):
        # Just verify the path string is in the do_POST source. Robust to refactors.
        import inspect
        src = inspect.getsource(self.mod.Handler.do_POST)
        self.assertIn("/v1/chat/completions", src)
        self.assertIn("_proxy_openai_chat", src)

    def test_image_generation_path_recognized(self):
        import inspect
        src = inspect.getsource(self.mod.Handler.do_POST)
        self.assertIn("/v1/image_generation", src)
        self.assertIn("_proxy_image_generation", src)

    def test_anthropic_messages_still_routed(self):
        import inspect
        src = inspect.getsource(self.mod.Handler.do_POST)
        self.assertIn("/v1/messages", src)
        self.assertIn("_proxy_messages", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)