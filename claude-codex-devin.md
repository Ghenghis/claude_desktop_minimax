Yes, this is possible for both Claude Desktop and Claude Code on Windows 11 using your MiniMax API key. Codex can also be configured to use MiniMax as a backup provider.
Here’s the practical reality and a clean setup kit.
1. Claude Code (CLI) — Fully Supported
This is the easiest and most reliable. MiniMax officially documents it.
Recommended location for keys (private folders):
Put your MiniMax key in something like:
C:\Private\minimax_key.txt or
G:\Private\minimax_key.txt or
S:\Private\minimax_key.txt
Then reference it so the key never sits in plain text in config files that might get synced.


Complete Markdown Guide
# MiniMax API Key Setup Guide  
**Claude Code · Claude Desktop · Codex**  
*(Windows 11 · Private Key Storage)*

Use your MiniMax Token Plan key to power Claude Code, Claude Desktop, and Codex.  
No Anthropic subscription is required when using the MiniMax endpoint.

---

## 1. Private Key Storage (Recommended)

Create a private folder (pick one):

- `C:\Private\`
- `G:\Private\`
- `S:\Private\`

Inside the folder create:
minimax_key.txt          ← paste your MiniMax API / Token Plan key here
minimax_env.ps1          ← optional loader script
**Example `minimax_env.ps1`:**

```powershell
# Load MiniMax key from private folder
$keyPath = "C:\Private\minimax_key.txt"   # change to G: or S: if needed
$env:MINIMAX_API_KEY = (Get-Content $keyPath -Raw).Trim()
$env:ANTHROPIC_AUTH_TOKEN = $env:MINIMAX_API_KEY
$env:ANTHROPIC_BASE_URL = "https://api.minimax.io/anthropic"
Write-Host "MiniMax environment loaded." -ForegroundColor Green
2. Claude Code (CLI) — Most Reliable Method
Official MiniMax support via Anthropic-compatible endpoint.
Config file location
%USERPROFILE%\.claude\settings.json
Recommended content
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "YOUR_MINIMAX_KEY_HERE",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "ANTHROPIC_MODEL": "MiniMax-M3[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M3[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M3[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M3[1m]"
  }
}
Alternative (safer): Leave the key out of the file and load it from the private folder with PowerShell before launching:
. C:\Private\minimax_env.ps1
claude
Verify
claude
/status
/model
You should see the MiniMax base URL and model.
3. Claude Desktop — Gateway Method
Open Claude Desktop.
Go to Help → Troubleshooting → Enable Developer Mode (the app will restart and show a Developer menu).
Open Developer → Configure Third-Party Inference.
Configure as follows:
Connection / Inference provider: Gateway
Gateway base URL: https://api.minimax.io/anthropic
Gateway API key: your MiniMax key
Auth scheme: Bearer (or the option that matches)
Apply the settings and relaunch Claude Desktop.
If you were previously logged into an Anthropic account, log out first.
Community tools such as mxclaude-desktop or ModelLink can automate writing the correct configuration on Windows if the manual form is stubborn.
4. Codex (OpenAI Codex)
MiniMax supports Codex via its OpenAI-compatible endpoint.
Config file location
%USERPROFILE%\.codex\config.toml
Recommended content
model = "MiniMax-M3"
model_provider = "minimax"
model_context_window = 1000000

[model_providers.minimax]
name = "MiniMax"
base_url = "https://api.minimax.io/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "responses"   # try "chat" if "responses" fails on your version
Set the key
$env:MINIMAX_API_KEY = (Get-Content "C:\Private\minimax_key.txt" -Raw).Trim()
Or load it with the private PowerShell script before starting Codex.
You can keep your normal OpenAI provider as primary and switch to the minimax provider when your main quota is exhausted (manual switch or simple wrapper script).
5. Devin / Windsurf (Devin Desktop) Status
Feature
Status
Native MiniMax endpoint
Not officially supported
Arbitrary custom Base URL
Generally not available
Official BYOK
Limited to specific providers (Claude, GPT, etc.)
Community workarounds
Exist (local proxies / BYOK bridges) but more complex
Recommendation: Use Devin/Windsurf on its own plans if you like the agent style. It does not currently offer the clean MiniMax integration that Claude Code, Claude Desktop, and Codex provide.
Quick Reference – Endpoints
Protocol
Base URL
Used By
Anthropic-compatible
https://api.minimax.io/anthropic
Claude Code, Claude Desktop
OpenAI-compatible
https://api.minimax.io/v1
Codex and many other tools
China users: replace with https://api.minimaxi.com/...
Recommended Daily Workflow
Primary high-volume agent → Claude Code + MiniMax
GUI preference → Claude Desktop (Gateway mode) + MiniMax
Codex backup → Switch to the MiniMax provider when your main Codex quota runs out
Keep Devin/Windsurf on its native subscription if you use it
One-Click Launcher Example (PowerShell)
Save as Start-ClaudeCode-MiniMax.ps1:
# Load private key
. "C:\Private\minimax_env.ps1"

# Optional: force model settings
$env:ANTHROPIC_MODEL = "MiniMax-M3[1m]"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = "MiniMax-M3[1m]"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL = "MiniMax-M3[1m]"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "MiniMax-M3[1m]"

# Launch Claude Code
claude
Create similar launchers for Claude Desktop and Codex as needed.
Last updated: August 2026
Always re-test after major updates to Claude Desktop or Codex.
This is a complete, self-contained Markdown file. You can copy the entire block above into a `.md` file.


=============================================================

Claude Code setup (Windows):
Install Claude Code normally.
Create/edit %USERPROFILE%\.claude\settings.json:
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "YOUR_MINIMAX_KEY_HERE",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "ANTHROPIC_MODEL": "MiniMax-M3[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M3[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M3[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M3[1m]"
  }
}
(Or load the key from your private file via a small PowerShell wrapper that sets the env var before launching claude.)
No Anthropic subscription is required.
2. Claude Desktop — Possible via Gateway Mode
Claude Desktop now supports third-party inference through its Gateway configuration (Developer Mode).
How to set it up on Windows 11:
Open Claude Desktop.
Go to Help → Troubleshooting → Enable Developer Mode (this restarts the app and adds a Developer menu).
Go to Developer → Configure Third-Party Inference.
Set:
Inference provider / Connection: Gateway
Gateway base URL: https://api.minimax.io/anthropic
Gateway API key: your MiniMax key
Auth scheme: Bearer (or whatever the UI shows as matching)
There are also community helper tools (e.g. dsclaude / mxclaude-desktop scripts and ModelLink) that automate writing the correct Claude Desktop config for MiniMax. These are useful if the manual Gateway form is finicky on Windows.
Note: Claude Desktop’s third-party support is newer and slightly less battle-tested than the CLI. Some users report needing to log out of any Anthropic account and relaunch after configuring the Gateway. The CLI path is currently more rock-solid.
3. Codex as Backup (Yes, Possible)
Codex supports custom providers. MiniMax has official docs for this.
You can add MiniMax as a second provider in \~/.codex/config.toml (or %USERPROFILE%\.codex\config.toml on Windows) using the OpenAI-compatible endpoint:
[model_providers.minimax]
name = "MiniMax"
base_url = "https://api.minimax.io/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "responses"   # or "chat" depending on current Codex version

# Then you can switch to it with:
# model_provider = "minimax"
# model = "MiniMax-M3"
Set the environment variable MINIMAX_API_KEY to point at your private key file.
Automatic fallback when tokens run out is not built-in. You would need either:
Manual switch (/model or profile change), or
A small wrapper/script that detects rate-limit/token-exhaustion errors and restarts Codex with the MiniMax profile.
Recommended Private Key Layout (Windows)
C:\Private\          (or G:\Private\ or S:\Private\)
├── minimax_key.txt          ← plain key (or encrypted)
├── minimax_env.ps1          ← PowerShell that loads the key into env vars
└── README.txt               ← your notes
Then create a launcher (e.g. desktop shortcut or batch/PowerShell) that:
Loads the key from the private folder into the environment
Starts Claude Desktop / Claude Code / Codex with the correct settings
Summary – What Works Today
Tool
MiniMax Support
Difficulty on Windows 11
Automatic backup ready?
Claude Code (CLI)
Excellent (official)
Easy
N/A
Claude Desktop
Yes (via Gateway)
Medium
N/A
Codex
Yes (custom provider)
Easy–Medium
Manual or scripted
Best practical path right now:
Use Claude Code + MiniMax as your high-volume primary agent (easiest + most reliable).
Configure Claude Desktop with the Gateway method for the GUI experience you prefer.
Add MiniMax as a second provider in Codex so you can switch to it when your main Codex quota is exhausted.
Would you like me to write the exact PowerShell launcher scripts + the private-folder structure + the full settings.json / config.toml files ready to copy-paste for Windows 11?