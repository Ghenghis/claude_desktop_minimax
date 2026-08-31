> HISTORICAL DOCUMENT — superseded by README.md and docs/SAFETY_REVIEW.md.
> Do not run old watchdog, permission-bypass, process-kill or repair instructions.

# Threat Model (STRIDE)

Asset: **the MiniMax API key**. Boundary: the proxy process on `127.0.0.1:48217`.

Distilled from `docs/admin-gateway-audit/06-bugs-and-polish.md` and the
deeper STRIDE audit at `docs/admin-gateway-audit/` (security audit bundle).

## STRIDE

| STRIDE | Threat | Mitigation | Status |
|---|---|---|---|
| **S**poofing | Local process poses as Claude Desktop and burns the user's quota | `X-Proxy-Token` shared-secret, constant-time compare, mode-0600 file | **Mitigated** (Gap 1) |
| **S**poofing | Local browser page calls the proxy via CORS | `do_OPTIONS` no longer wildcard-CORS | **Mitigated** (Gap 3) |
| **T**ampering | Client injects its own `Authorization`/`X-Api-Key` | Both headers stripped; proxy injects its own key from `.env` | **Mitigated** |
| **T**ampering | Client targets internal preview model (`MiniMax-M3-experimental`) | Multimodal allowlist is exact-match (no prefix matching) | **Mitigated** |
| **R**epudiation | No record of who called | stderr log: method + path + status; HermesProof evidence ledger for Skills | **Partial** — no per-PID identity |
| **I**nfo disclosure | Key leaks to logs | Only byte-length logged; never the value | **Mitigated** |
| **I**nfo disclosure | Key leaks to registry | Registry holds `proxy-managed` placeholder; real key never written there | **Mitigated** |
| **I**nfo disclosure | Key leaks to PowerShell history | `Load-MinimaxKey.ps1` uses `$env:` (process scope), not `[Environment]::SetEnvironmentVariable` | **Mitigated** |
| **I**nfo disclosure | `.env` file readable by other users | `Harden-MinimaxEnv.ps1` disables inheritance, denies Everyone, owner-only | **Mitigated** |
| **D**oS | Oversized body exhausts memory | `Content-Length` capped at 50 MB on all POST paths | **Mitigated** (bug #6) |
| **D**oS | Hung-but-listening proxy (urlopen stuck) | Watchdog now probes `/readyz`, not just TCP listen | **Mitigated** (bug #8) |
| **E**oP | Off-host attacker reaches proxy | Binds `127.0.0.1` only | **Mitigated** |

## Accepted risks

- Any local process running as this user can read `G:\private\.env` and the
  proxy token file. The proxy is a single-user tool; the trust boundary is
  the user account, not the network.
- No per-IP rate limiting. A local caller can exhaust the MiniMax quota if
  it bypasses the token check (which would require either a token leak or
  a separate OS-level compromise).
- The shared-secret token is read from a file on disk. If the file is
  world-readable, the secret is compromised. `scripts/Generate-ProxyToken.ps1`
  ACL's the file at generation time.

## Review trigger

Re-review this document on any change to:

- Auth (`X-Proxy-Token`, key loading, header injection)
- Network binding (port, interface)
- Logging (`stderr` content, rotation, redaction)

**Last reviewed:** 2026-08-13.

## Out-of-scope

- MiniMax API vulnerabilities — report upstream.
- Attacks requiring Administrator on the host.
- Claude Desktop permission-mode toggle bug (#61304) — tracked upstream.