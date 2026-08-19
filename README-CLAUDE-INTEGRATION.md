# DAVE-AI Agent Harness — Claude Desktop Integration

Project root: `C:\Users\Admin\claude-codex-devin`

## What is already in place

- **Contracts**: `contracts\DAVEAI_HARNESS_CONTRACT.yaml`, `contracts\KEY_TOOL_CONTRACTS.yaml`, and `contracts\tool_contract.schema.json`.
- **Project state**: `.agent\` with `AUTHORIZED_SCOPE.md`, `HARNESS_CONTRACT.yaml`, `PROJECT_STATE.md`, `PROOF_LEDGER.md`, and `evidence/` / `reports/` folders.
- **Preflight**: `.agent\DAVEAI-preflight.json` (PATH-only, safe) shows which RE/Android/Windows tools are available.
- **Skills**: `.claude\skills\` contains the DAVE-AI skill set:
  - `daveai-android-e2e`, `daveai-apk-re-triage`, `daveai-capability-doctor`, `daveai-privacy-mode`, `daveai-project-intake`, `daveai-proof-ledger`, `daveai-recovery-handoff`, `daveai-skill-vetter`, `daveai-unity-re-router`, `daveai-web-e2e`, `daveai-windows-app-e2e`, `daveai-windows-re-triage`.
- **MCP examples**: `configs\mcp-examples\` has starter JSON for `serena-claude-desktop`, `scrcpy-mcp`, `x64dbg-automate`, `playwright-mcp`, `radare2-mcp`, `maestro-mcp`, `jadx-ai-mcp`, `ghidra-headless`, `gitlab-mcp`, `hyperv-mcp`, and `android-mcp-lean-alternative`.

## Recommended CORE profile for this workspace

Per `DAVEAI_Agent_Harness\profiles\CORE.yaml`:

- Always enable:
  - `daveai-project-intake`
  - `daveai-capability-doctor`
  - `daveai-proof-ledger`
  - `daveai-recovery-handoff`
  - `daveai-skill-vetter`
  - `daveai-privacy-mode`
- Use on demand:
  - `github_or_gitlab_connector`
  - `trailofbits_curated_individual_skill`
- Never enable by default:
  - `frida`, `debugger`, `hyperv`, `unrestricted_shell_mcp`, `public_network_mcp_binding`

## How to load into Claude Desktop

1. Open Claude Desktop.
2. Make sure this folder (`C:\Users\Admin\claude-codex-devin`) is used as the project workspace.
3. Claude Desktop will load the local `.claude\skills\` automatically if the project is selected.
4. If the UI does not auto-detect skills, use the **Skills** tab and add each `.claude\skills\daveai-*` directory.

## One-step setup and verification

Run the gateway linker from the project root:

```powershell
.\Set-ClaudeDesktopGateway.ps1
```

This single script:

1. Loads the MiniMax key from `G:\private\.env` (the key is never written to the registry).
2. Wires `HKCU:\SOFTWARE\Policies\Claude` so Claude Desktop uses the local MiniMax proxy at `http://127.0.0.1:<port>/anthropic`.
3. Registers the three always-on stdio MCP servers in `managedMcpServers`:
   - `minimax-media` — `G:\Github\Testing-Claude-Minimax-Mcp\minimax-mcp-server\server.py`
   - `hermes3d-locks` — `G:\Github\hermes3d-mcp-lock-orchestrator\src\server.mjs` with `MCP_LOCK_WORKSPACE` set to this project root
   - `serena-semantic` — `serena start-mcp-server --context=desktop-app`

The script auto-discovers a Python runtime that has the `mcp` package and validates that the server files exist before writing the registry. If a server is missing, it stops and tells you what is missing instead of leaving Claude Desktop in a broken state.

### Manual fallback

If you prefer not to run the script, starter snippets are in `configs\mcp-examples\` for `serena-claude-desktop`, `scrcpy-mcp`, `playwright-mcp`, `radare2-mcp`, etc. Copy the relevant `.json` into `claude_desktop_config.json` and replace `<PATH_TO_REPO>` / `<PROJECT_ROOT>`.

## Smoke-test

Before using any profile, run a single harmless request, for example:

- "Load the DAVE-AI CORE profile and summarize the current project state from `.agent\PROJECT_STATE.md`."

If that succeeds, the integration is working. Then pick a specific profile (RE, Android, Windows) only when needed.

## Serena verification

`serena-agent` v1.7.0 was installed via `uv tool install -p 3.13 serena-agent` and wired into `HKCU:\SOFTWARE\Policies\Claude\managedMcpServers` as `serena-semantic` using the canonical command `serena start-mcp-server --context=desktop-app`.

MCP initialize smoke-test returned:

- `serverInfo.name` = `Serena`
- `serverInfo.version` = `1.28.1`
- `tools` / `prompts` / `resources` capabilities present

Live tool tests performed:

- `activate_project` with the absolute path `C:\Users\Admin\claude-codex-devin` succeeded.
- `list_dir` returned the project tree.
- `search_for_pattern` found 7 hits for `OPENAI_BASE|MODEL_MAP|inferenceGatewayBaseUrl` in `claude-minimax-proxy.py`.
- `get_symbols_overview` on `Set-ClaudeDesktopGateway.ps1` found 11 variables (PowerShell LSP currently exposes only `Variable` kinds, not `Function`).
- `read_file` with line range `235-260` returned the `MODEL_MAP` and `pick_minimax_model` definitions.

Known limitations:

- Python symbol extraction requires the Python LSP, which is downloaded lazily on first use.
- `.ps1` functions are not exposed by the PowerShell LSP; use `replace_content` or `replace_in_files` for PowerShell edits.

## Next user action

1. Restart Claude Desktop after running `.\Set-ClaudeDesktopGateway.ps1`.
2. Select this workspace (`C:\Users\Admin\claude-codex-devin`).
3. Confirm the DAVE-AI skills appear under **Skills**.
4. Confirm these three MCP servers appear and are enabled in the **MCP** list:
   - `minimax-media`
   - `hermes3d-locks`
   - `serena-semantic`
5. Run the built-in smoke-test prompt: "Load the DAVE-AI CORE profile and summarize `.agent\PROJECT_STATE.md`.
6. Only then load a target profile (RE, Android, Windows) for a real task.
