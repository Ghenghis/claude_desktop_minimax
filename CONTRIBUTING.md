# Contributing

## Setup

1. `pip install pre-commit && pre-commit install`
2. Put your MiniMax key in `G:\private\.env` as `MINIMAX_API_KEY=...`
3. `powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-ClaudeMiniMaxProxy.ps1`

## Before you push

- `python tests/test_proxy_e2e.py` — 26 tests, no network needed
- `pre-commit run --all-files`

## Review standard

A change is approved when it **improves overall code health** — not when it
is perfect. See Google's [Standard of Code Review](https://google.github.io/eng-practices/review/reviewer/standard.html).
Optional suggestions are prefixed `Nit:` and never block a merge.

## Commits

Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
The PR template requires `CHANGELOG.md` update under `[Unreleased]`.

## Never commit

API keys, `G:\private\*` contents, `AICE_DATA/`, `__pycache__/`.
`.gitignore` enforces this but please don't try to work around it.

## Adding a Skill

1. Create `.harness/skills/<your-skill>/SKILL.md` with the structure described
   in `.harness/HARNESS.md` (frontmatter + inputs + procedure + hermes_trace +
   outputs + examples).
2. If it accepts inputs, add a JSON Schema under `.harness/contracts/`.
3. Add the HermesProof trace section listing which `hermes_*` tool calls it makes.
4. Add a test under `tests/test_<your-skill>.py`.

## Adding an MCP connector

1. Document under `.harness/connectors/<name>.md` with: URL, install command,
   required env vars, transport.
2. Add the entry to `Set-ClaudeDesktopGateway.ps1`'s `$managedMcpServers`.