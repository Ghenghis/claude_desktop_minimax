# Security Policy

## Supported versions

The `main` branch only. Older commits are not security-supported.

## Reporting a vulnerability

Open a **private** GitHub security advisory at
`https://github.com/<owner>/claude-codex-devin/security/advisories/new`.
Do **not** open a public issue for a vulnerability.

Initial response within **14 days**.

## Scope

This proxy holds a live MiniMax API key in process memory and reads it from
`G:\private\.env`. Report anything that could:

- Expose the MiniMax API key (in logs, error messages, registry values, or HTTP responses)
- Allow a non-loopback client to reach the proxy
- Bypass the shared-secret `X-Proxy-Token` client auth
- Bypass the multimodal model allowlist (allow `MiniMax-M3-experimental` etc.)
- Exfiltrate `.env` content to any caller

## Out of scope

- MiniMax API vulnerabilities (report upstream to MiniMax)
- Attacks requiring Administrator on the host
- Claude Desktop's own permission-mode toggle bug (#61304) — tracked upstream

## Threat model

See [`docs/threat-model.md`](docs/threat-model.md) for the full STRIDE analysis.

## Hardening utilities

- `scripts/Generate-ProxyToken.ps1` — generate the shared-secret token
- `Harden-MinimaxEnv.ps1` — set restrictive ACL on `G:\private\.env`
- `Fix-ClaudePermissions.ps1` — work around Claude Desktop broken toggle
- `.claude/verifiers/run.sh` — pre-commit quality gate