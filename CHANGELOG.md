# Changelog

All notable changes to the Admin Gateway are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/1.1.0/).
Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Shared-secret proxy token auth (`X-Proxy-Token` header; token file at `G:\private\.proxy-token`).
- Multimodal model allowlist (exact-match; closes security Gap 3 from STRIDE threat model).
- `/healthz` and `/readyz` admin endpoints for watchdog probes.
- In-memory `.env` key cache with mtime hot-reload (no proxy restart on key rotation).
- SHA-256 exact-match cache for `/v1/messages` responses (24h TTL, 512-entry LRU).
- Retry-with-backoff + `Retry-After` honor (3 attempts; 408/425/429/5xx).
- Model Chains waterfall (`claude-sonnet-4-5` → M3 → M2.7 → M2.7-highspeed; etc.).
- New proxy endpoints: `/v1/chat/completions` (OpenAI-compat), `/v1/image_generation` (sync T2I).
- Body-size cap (50 MB) on `/v1/messages` (closes bug #6).
- Unknown picker model → 400 (closes bug #7; no silent flagship fallback).
- `.harness/HARNESS.md` + 6 Skills under `.harness/skills/` (cost-report, cache-tune, watchdog-self-test, failover-drill, permission-repair, playwright-verify).
- `.harness/contracts/proxy-config.schema.json` + `skill-input.schema.json`.
- `scripts/hermes-call.ps1` for Skills to record HermesProof evidence.
- `scripts/Generate-ProxyToken.ps1` for the shared-secret token.
- `Fix-ClaudePermissions.ps1` to work around Claude Desktop #61304 (broken "Bypass permissions" toggle).
- `.claude/{principles.md, CLAUDE.md, notes.md, verifiers/run.sh}` for agent context + verifier chain.
- `tests/test_proxy_e2e.py` — 26 stdlib unit tests, all passing.
- `.pre-commit-config.yaml` (flake8 + py_compile).
- `docs/admin-gateway-audit/` — 6-document audit bundle (current features, competitive analysis, recommendations, MiniMax extension, SOTA game-changers, bugs-and-polish).
- `docs/architecture.md`, `docs/threat-model.md`, `docs/adr/0001-model-renaming-proxy.md`.
- `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.

### Changed
- `claude-minimax-proxy.py` parses + runs as a stdlib-only Python 3.10+ HTTP server.

### Fixed
- Bug #16: `_parse_dotenv` now skips empty values (`MINIMAX_API_KEY=""` fails loudly).
- Bug #8 (partial): `Watch-ClaudeMiniMaxProxy.ps1` now probes `/readyz` in addition to TCP listen.

### Security
- Client auth required on all mutating endpoints (`X-Proxy-Token` constant-time compare).
- `do_OPTIONS` no longer wildcard-CORS — closes the "any local browser" attack.
- Model name allowlist is exact-match; prefix matching (which would have allowed `MiniMax-M3-experimental`) removed.

## [1.0.0] - 2026-08-10

### Added
- Claude Desktop ↔ MiniMax model-renaming proxy on `127.0.0.1:48217`.
- Watchdog with 15-second health polling (`Watch-ClaudeMiniMaxProxy.ps1`).
- `.env` ACL hardening (`Harden-MinimaxEnv.ps1`).
- One-command setup (`Start-ClaudeMiniMaxProxy.ps1`).
- 14 regression tests covering validation, request encoding, collision-safe files, async responsiveness, timeout behavior, and launcher startup.