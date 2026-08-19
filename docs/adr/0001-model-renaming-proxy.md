# ADR 1: Rename models in a local proxy

**Date:** 2026-08-13
**Status:** Accepted

## Context

Claude Desktop's third-party gateway mode rejects non-Anthropic model IDs in
`inferenceModels`. We want Claude Desktop to talk to MiniMax (a different
vendor) without patching the desktop client.

Options:

- **(a)** Patch Claude Desktop — fragile, breaks on every desktop update.
- **(b)** Run a local translating proxy — survives client updates; single
  point of credential injection.
- **(c)** Wait for Claude Desktop upstream to support non-Anthropic model
  names in `inferenceModels`.

## Decision

Run a local loopback HTTP proxy that accepts an Anthropic-looking model ID
(such as `claude-sonnet-4-5`) and rewrites the `model` field to a MiniMax
model (such as `MiniMax-M3`) before forwarding to `https://api.minimax.io/anthropic/v1/messages`.

The proxy:

- Binds `127.0.0.1:48217` (loopback only).
- Always strips client-supplied `Authorization` / `X-Api-Key`.
- Always injects the real key from `G:\private\.env`.
- Requires `X-Proxy-Token` (shared secret) on every POST endpoint.
- Enforces an exact-match allowlist on multimodal endpoints.
- Falls back through a Model Chains waterfall on upstream 5xx.

## Consequences

**Good:**

- No client patching; survives Claude Desktop updates.
- Centralises the API key so it never reaches the client or registry.
- A single chokepoint to add caching, retries, observability, and fail-over.

**Bad:**

- A proxy process must be running (mitigated by the watchdog).
- Adds a network hop (negligible latency on loopback).
- The picker-to-model map needs updating when MiniMax renames models.

## Alternatives rejected

- **Forking Claude Desktop** — every desktop update becomes a fork-maintenance burden.
- **Direct `inferenceModels: ["MiniMax-M3"]`** — Claude Desktop validates that
  the model name starts with `claude-`; rejected with `unstableDisableModelVerification`
  being unreliable across versions.
- **Pre-Anthropic-spec OpenAI-compat path** — Claude Desktop doesn't expose an
  OpenAI-compat inference mode in the registry.

## References

- `claude-minimax-proxy.py` — implementation
- `docs/architecture.md` — request flow
- `docs/admin-gateway-audit/06-bugs-and-polish.md` — known issues