# Fix the known, safe real gaps for Claude-Desktop MiniMax V2 release.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# --- 1. git / gh / glab CLI presence ---
Write-Host '--- CLI presence check ---' -ForegroundColor Cyan
$git = Get-Command 'git.exe' -ErrorAction SilentlyContinue
$gh = Get-Command 'gh.exe' -ErrorAction SilentlyContinue
$glab = Get-Command 'glab.exe' -ErrorAction SilentlyContinue

if ($git) { Write-Host "git OK: $($git.Source)" -ForegroundColor Green } else { Write-Warning 'git CLI not on PATH' }
if ($gh) { Write-Host "gh OK: $($gh.Source)" -ForegroundColor Green } else { Write-Warning 'gh CLI not on PATH' }
if ($glab) { Write-Host "glab OK: $($glab.Source)" -ForegroundColor Green } else { Write-Warning 'glab CLI not on PATH. Install: winget install glab or see https://gitlab.com/gitlab-org/cli' }

# --- 2. OpenHands / Hermes Agent bridge ---
Write-Host '--- OpenHands / Hermes Agent bridge ---' -ForegroundColor Cyan
$agentEnabled = $env:HERMES_AGENT_ENABLED
$openhandsUrl = $env:OPENHANDS_URL

if ($agentEnabled -ne '1') {
    [Environment]::SetEnvironmentVariable('HERMES_AGENT_ENABLED', '1', 'User')
    $env:HERMES_AGENT_ENABLED = '1'
    Write-Host 'Set HERMES_AGENT_ENABLED=1' -ForegroundColor Green
} else {
    Write-Host 'HERMES_AGENT_ENABLED already 1' -ForegroundColor Green
}

if (-not $openhandsUrl) {
    # Prefer local OpenHands; user can override.
    $defaultUrl = 'http://127.0.0.1:3333'
    [Environment]::SetEnvironmentVariable('OPENHANDS_URL', $defaultUrl, 'User')
    $env:OPENHANDS_URL = $defaultUrl
    Write-Host "Set OPENHANDS_URL=$defaultUrl" -ForegroundColor Green
} else {
    Write-Host "OPENHANDS_URL already set: $openhandsUrl" -ForegroundColor Green
}

# --- 3. Provider registry placeholder ---
Write-Host '--- Provider registry ---' -ForegroundColor Cyan
$regPath = $env:HERMES_PROVIDER_REGISTRY
if (-not $regPath) {
    $defaultReg = 'G:\Github\claude-codex-devin\.hermes3d_orchestrator\provider_registry.json'
    New-Item -ItemType Directory -Path (Split-Path -Parent $defaultReg) -Force -ErrorAction SilentlyContinue | Out-Null
    if (-not (Test-Path $defaultReg)) {
        @{} | ConvertTo-Json | Set-Content -Path $defaultReg -Encoding UTF8
    }
    [Environment]::SetEnvironmentVariable('HERMES_PROVIDER_REGISTRY', $defaultReg, 'User')
    $env:HERMES_PROVIDER_REGISTRY = $defaultReg
    Write-Host "Set HERMES_PROVIDER_REGISTRY=$defaultReg" -ForegroundColor Green
} else {
    Write-Host "HERMES_PROVIDER_REGISTRY already set: $regPath" -ForegroundColor Green
}

# --- 4. Claude_Browser launch target ---
Write-Host '--- Claude_Browser launch target ---' -ForegroundColor Cyan
$claudeDir = Join-Path $env:USERPROFILE '.claude'
$launchJson = Join-Path $claudeDir 'launch.json'
if (-not (Test-Path $launchJson)) {
    New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
    @{
        targets = @(
            @{
                name = 'claude-minimax-gateway'
                url = 'http://127.0.0.1:48217'
            },
            @{
                name = 'local-playground'
                url = 'http://127.0.0.1:3000'
            }
        )
    } | ConvertTo-Json -Depth 5 | Set-Content -Path $launchJson -Encoding UTF8
    Write-Host "Created $launchJson" -ForegroundColor Green
} else {
    Write-Host "$launchJson already exists" -ForegroundColor Green
}

# --- 5. GLAB token shell hint ---
Write-Host '--- GitLab token note ---' -ForegroundColor Cyan
$gitlabToken = $env:GITLAB_TOKEN
if (-not $gitlabToken) {
    Write-Warning 'GITLAB_TOKEN not in shell env. If glab is installed, source the operator env file or run: [Environment]::SetEnvironmentVariable(''GITLAB_TOKEN'', ''<token>'', ''User'')'
} else {
    Write-Host 'GITLAB_TOKEN present in shell env' -ForegroundColor Green
}

Write-Host '--- Fix complete. Restart your shell or IDE for env vars to take full effect. ---' -ForegroundColor Green
