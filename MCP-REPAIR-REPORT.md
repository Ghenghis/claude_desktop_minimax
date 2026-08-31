> HISTORICAL DOCUMENT — superseded by README.md and docs/SAFETY_REVIEW.md.
> Do not run old watchdog, permission-bypass, process-kill or repair instructions.

# MCP Repair and Reliability Report

Date: 2026-08-22
Scope: Claude Desktop + Codex Desktop shared `mini` MCP layer on Windows

## Executive result

The two MCPs shown in the user's screenshot were installed and repaired:

| MCP | Runtime | Verified result |
|---|---|---|
| `touchpoint` | Isolated C: venv, direct executable | PASS — 27 tools; direct initialize and `mini ls` pass |
| `winremote` | Isolated C: venv, direct executable | PASS — 20 tools; direct initialize and `mini ls` pass |

Both clients consume the same `mini` registry, so these tools are available to
both Claude Desktop and Codex Desktop through their existing `mini connect`
configuration.

## Repairs performed

1. Installed `touchpoint-py` in `C:\Users\Admin\claude-codex-devin\venvs\touchpoint`.
2. Installed the missing MCP 1.x runtime into that venv. The original failure
   was `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`.
3. Installed `winremote-mcp` in
   `C:\Users\Admin\claude-codex-devin\venvs\winremote`.
4. Replaced `.cmd` indirection in `mini` with direct executable paths. This
   avoids Windows command-wrapper behavior and makes child errors visible.
5. Configured Touchpoint with vision mode, CDP discovery, and fallback input.
6. Configured WinRemote with stdio and `--disable-tier2`. Tier 3 remains off.
   This exposes read-only Windows inspection without enabling interactive or
   destructive desktop control by default.
7. Added both MCP checks to `Test-MiniMaxStack.ps1`.

## Current healthy MCP set

- `Windows-MCP` — 18 tools
- `chrome-devtools` — 29 tools
- `daves-tools-harness` — 8 tools
- `hermes3d-locks` — 121 tools
- `hp-mha-serena` — 34 tools
- `minimax-media` — 9 tools (speech, image, video, music, files, Video Agent templates)
- `minimax` official — 8 tools
- `minimax-coding-plan` — 2 tools (`web_search`, `understand_image`)
- `node_repl` — 3 tools
- `touchpoint` — 27 tools
- `winremote` — 20 tools

## Remaining non-MCP blockers

### Unity MCP

`unityMCP` is an HTTP server configured for `http://127.0.0.1:8080/mcp`.
It fails because no Unity Editor/plugin is currently listening on port 8080.
This is not repairable by changing the client registry alone. Launch the
intended Unity project with its MCP package and verify the endpoint before
adding it to an always-on profile.

### Serena duplicates

There are two configurations (`serena` and `serena-semantic`) and multiple
leftover processes from earlier probes. The stale one previously used `uvx` and
`G:\Github\HermesProof`; the local one uses the C: daves-tools venv. The
healthy `hp-mha-serena` server already exposes 34 tools. Keep one Serena
instance per project; do not auto-start duplicate indexers in both clients.

### Cold-start behavior

`mini status` probes every configured server concurrently. On this host, many
Python/Node MCPs can exceed the global probe deadline during a cold start and
leave child processes behind. Direct MCP handshakes pass. Use targeted
`mini ls <server>` for proof of one server, and use the health harness after a
warm-up rather than treating one cold `status` failure as a package failure.

## Reproducible evidence

```powershell
& 'C:\Users\Admin\go\bin\mini.exe' ls touchpoint
& 'C:\Users\Admin\go\bin\mini.exe' ls winremote
& 'C:\Users\Admin\claude-codex-devin\Test-MiniMaxStack.ps1' -Fix
```

Expected targeted counts: Touchpoint 27, WinRemote 20.

## Security posture

- WinRemote Tier 3 is disabled.
- WinRemote Tier 2 is disabled by default in the shared registry.
- No remote bind or network exposure was enabled.
- No secrets were written into MCP YAML files.
- MiniMax credentials remain in `C:\private\.env`.
