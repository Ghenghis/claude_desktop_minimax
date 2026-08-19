# Workaround for Claude Desktop "Bypass permissions" error:
#   "Permission mode couldn't be changed. You can try again."
#
# Root cause (anthropics/claude-code #61304): the desktop app spawns the embedded
# CLI with `--permission-mode default` instead of the bypass flag, so the UI
# toggle fails silently and falls back to `acceptEdits`.
#
# This script applies both known workarounds:
#   1. Edit %APPDATA%\Claude\settings.json to pin the permission mode
#   2. Add a launcher that calls Claude Code CLI with --dangerously-skip-permissions
#      when you really want unattended execution.
#
# Neither workaround restores the broken toggle. The toggle stays broken until
# Claude Desktop ships a fix. Until then, this gives you the equivalent behavior
# without waiting on the UI.
#
# Run interactively from PowerShell (no admin needed):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\Fix-ClaudePermissions.ps1
#
# Run with -Undo to restore the original settings.json.
#
# What it does NOT do:
#   - Touch the Admin Gateway proxy
#   - Touch MiniMax credentials
#   - Touch the Claude registry keys that wire Claude Desktop to the gateway

[CmdletBinding()]
param(
    [switch]$Undo
)

$ErrorActionPreference = 'Stop'
$settingsPath = Join-Path $env:APPDATA "Claude\settings.json"
$backupPath = "$settingsPath.fix-ps1.bak"

function Backup-If-Needed {
    if (Test-Path -LiteralPath $settingsPath) {
        if (-not (Test-Path -LiteralPath $backupPath)) {
            Copy-Item -LiteralPath $settingsPath -Destination $backupPath
            Write-Host "Backed up $settingsPath -> $backupPath" -ForegroundColor DarkGray
        } else {
            Write-Host "Backup already exists at $backupPath" -ForegroundColor DarkGray
        }
    }
}

function Read-Settings {
    if (-not (Test-Path -LiteralPath $settingsPath)) { return @{} }
    try {
        $raw = Get-Content -LiteralPath $settingsPath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
        return ($raw | ConvertFrom-Json -AsHashtable)
    } catch {
        Write-Warning "Could not parse $settingsPath as JSON: $_"
        return @{}
    }
}

function Write-Settings {
    param($settings)
    $dir = Split-Path -Parent $settingsPath
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $settings | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
}

if ($Undo) {
    if (Test-Path -LiteralPath $backupPath) {
        Copy-Item -LiteralPath $backupPath -Destination $settingsPath -Force
        Write-Host "Restored $settingsPath from backup." -ForegroundColor Green
    } else {
        Write-Warning "No backup found at $backupPath; nothing to undo."
    }
    return
}

# --- Apply fix #1: pin permissions in settings.json ---
Backup-If-Needed
$settings = Read-Settings

# Anthropic's settings.json schema accepts `permissions` as a top-level object.
# We set defaultMode to "bypassPermissions" which the desktop app should pick up.
# Note: this setting is documented as of Claude Desktop 2.1.x; older builds may
# silently ignore it, in which case fix #2 below is required.
if (-not $settings.ContainsKey('permissions')) {
    $settings['permissions'] = @{}
}
$settings['permissions']['defaultMode'] = 'bypassPermissions'

Write-Settings $settings
Write-Host "[1/2] Pinned permissions.defaultMode = bypassPermissions in $settingsPath" -ForegroundColor Green
Write-Host "      Restart Claude Desktop for this to take effect." -ForegroundColor Yellow

# --- Fix #2: documented launcher that uses --dangerously-skip-permissions ---
# This is the canonical fix when the toggle stays broken: launch Claude Code
# directly with the CLI flag the desktop app refuses to set.
$launcherPath = Join-Path $PSScriptRoot "Start-ClaudeCode-BypassPermissions.ps1"
$launcherContent = @"
# Launcher that bypasses the broken Claude Desktop toggle.
# Calls Claude Code CLI with --dangerously-skip-permissions, which is equivalent
# to what the desktop "Bypass permissions" toggle is supposed to do.
#
# Use only when you understand the implications: every tool call is auto-approved.
# Stop with Ctrl+C.
`$ErrorActionPreference = 'Stop'
`$node = (Get-Command node.exe -ErrorAction Stop).Source
`$claude = (Get-Command claude.cmd -ErrorAction SilentlyContinue).Source
if (-not `$claude) {
    throw "Claude Code CLI not on PATH. Install from https://docs.claude.com/claude-code."
}
& `$claude --dangerously-skip-permissions @args
"@
Set-Content -LiteralPath $launcherPath -Value $launcherContent -Encoding UTF8
Write-Host "[2/2] Wrote launcher: $launcherPath" -ForegroundColor Green
Write-Host "      Run with: powershell -NoProfile -File .\$([System.IO.Path]::GetFileName($launcherPath))" -ForegroundColor Yellow

Write-Host ""
Write-Host "If the toggle still shows 'Permission mode couldn't be changed'," -ForegroundColor Yellow
Write-Host "the desktop app needs an update from Anthropic. Track:" -ForegroundColor Yellow
Write-Host "  https://github.com/anthropics/claude-code/issues/61304" -ForegroundColor Cyan
Write-Host "  https://github.com/anthropics/claude-code/issues/61415" -ForegroundColor Cyan