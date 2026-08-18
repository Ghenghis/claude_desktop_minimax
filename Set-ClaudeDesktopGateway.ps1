[CmdletBinding()]
param(
    [int]$ProxyPort = 0
)

# Load keys from G:\private\.env into THIS process only (Load-MinimaxKey.ps1
# never prints, returns, or persists the value).
. $PSScriptRoot\Load-MinimaxKey.ps1

$githubRoot = Split-Path -Parent $PSScriptRoot
$portFile = Join-Path $githubRoot "claude-minimax-v2\.port"

$port = if ($ProxyPort -gt 0) { $ProxyPort } elseif (Test-Path $portFile) {
    [int](Get-Content -Path $portFile -TotalCount 1)
} else { 48217 }

$regPath = "HKCU:\\SOFTWARE\\Policies\\Claude"
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }

Set-ItemProperty -Path $regPath -Name "inferenceProvider" -Value "gateway" -Type String
# Proxy mode: Claude Desktop talks to the local V2 proxy.  The actual port can be
# 48217 or an auto-discovered free port written to claude-minimax-v2\.port.
Set-ItemProperty -Path $regPath -Name "inferenceGatewayBaseUrl" -Value "http://127.0.0.1:$port/anthropic" -Type String
# PLACEHOLDER: Claude Desktop requires a non-empty value here, but the proxy
# ignores what Claude sends and always uses the key from G:\private\.env.
# Never write the real key to the registry -- it would be plaintext on disk.
Set-ItemProperty -Path $regPath -Name "inferenceGatewayApiKey" -Value "proxy-managed" -Type String
Set-ItemProperty -Path $regPath -Name "inferenceGatewayAuthScheme" -Value "x-api-key" -Type String
Set-ItemProperty -Path $regPath -Name "modelDiscoveryEnabled" -Value "true" -Type String
# Six Claude-family picker slots.  The V2 gateway maps these aliases to MiniMax text models:
#   claude-sonnet-*  -> MiniMax-M3
#   claude-opus-*    -> MiniMax-M2.7
#   claude-haiku-*   -> MiniMax-M2.7-highspeed
# `labelOverride` re-labels the picker; `name` is still the ID the gateway accepts.
$models = @(
    @{ name="claude-sonnet-4-5"; labelOverride="MiniMax M3"; anthropicFamilyTier="sonnet"; supports1m=$true; isFamilyDefault=$true },
    @{ name="claude-opus-4-6"; labelOverride="MiniMax M2.7"; anthropicFamilyTier="opus"; isFamilyDefault=$true },
    @{ name="claude-haiku-4-5"; labelOverride="MiniMax M2.7 Highspeed"; anthropicFamilyTier="haiku"; isFamilyDefault=$true },
    @{ name="claude-sonnet-4"; labelOverride="MiniMax M3 (legacy)"; anthropicFamilyTier="sonnet"; supports1m=$true },
    @{ name="claude-opus-4"; labelOverride="MiniMax M2.7 (legacy)"; anthropicFamilyTier="opus" },
    @{ name="claude-haiku-4"; labelOverride="MiniMax M2.7 Highspeed (legacy)"; anthropicFamilyTier="haiku" }
) | ConvertTo-Json -Depth 10 -Compress
Set-ItemProperty -Path $regPath -Name "inferenceModels" -Value $models -Type String
Remove-ItemProperty -Path $regPath -Name "unstableDisableModelVerification" -ErrorAction SilentlyContinue

# Local stdio MCP servers, always available in every chat:
#   hermes3d-locks / hp-mha-serena -> HermesProof multi-agent coordination + Serena semantic tools
#   minimax-media                  -> MiniMax voice (T2A), image, and video generation tools
$githubRoot = Split-Path -Parent $PSScriptRoot
$hermesProofRoot = Join-Path $githubRoot "hermes3d-mcp-lock-orchestrator"
$nodeCommand = (Get-Command node.exe -ErrorAction Stop).Source
# MiniMax media MCP: find a Python runtime that has the `mcp` package.
# Claude Desktop's stdio transport is fragile through PowerShell, so we
# register the actual python.exe plus server.py as the command/args.
$minimaxServer = Join-Path $githubRoot "Testing-Claude-Minimax-Mcp\minimax-mcp-server\server.py"

if (-not (Test-Path -LiteralPath $minimaxServer -PathType Leaf)) {
    throw "Required MCP server is missing: $minimaxServer"
}

$pythonCandidates = @(
    $env:MINIMAX_MCP_PYTHON,
    "C:\Python314\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
) | Where-Object { $_ }

$pythonPath = $null
foreach ($candidate in $pythonCandidates) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    & $candidate -c "from mcp.server.fastmcp import FastMCP" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pythonPath = $candidate
        break
    }
}

if (-not $pythonPath) {
    throw "No Python runtime with the 'mcp' package found. Install the minimax-mcp-server requirements.txt."
}

$managedMcpServers = @(
    @{
        name = "minimax-media"
        transport = "stdio"
        command = $pythonPath
        args = @($minimaxServer)
        toolPolicy = @{ "*" = "allow" }
    }
)

if (Test-Path (Join-Path $hermesProofRoot "src\server.mjs")) {
    $managedMcpServers += @{
        name = "hermes3d-locks"
        transport = "stdio"
        command = $nodeCommand
        args = @((Join-Path $hermesProofRoot "src\server.mjs"))
        env = @{ MCP_LOCK_WORKSPACE = $PSScriptRoot }
        toolPolicy = @{ "*" = "allow" }
    }
}

if (Test-Path (Join-Path $hermesProofRoot "src\hp-mha-serena\server.mjs")) {
    $managedMcpServers += @{
        name = "hp-mha-serena"
        transport = "stdio"
        command = $nodeCommand
        args = @((Join-Path $hermesProofRoot "src\hp-mha-serena\server.mjs"))
        env = @{
            MCP_LOCK_WORKSPACE = $PSScriptRoot
            HERMES_WORKSPACE_ROOT = $PSScriptRoot
        }
        toolPolicy = @{ "*" = "allow" }
    }
}

$managedMcpServers = $managedMcpServers | ConvertTo-Json -Depth 10 -Compress
Set-ItemProperty -Path $regPath -Name "managedMcpServers" -Value $managedMcpServers -Type String
Set-ItemProperty -Path $regPath -Name "isLocalDevMcpEnabled" -Value "true" -Type String

Write-Host "Claude Desktop 3P gateway configured. Restart Claude Desktop." -ForegroundColor Green
