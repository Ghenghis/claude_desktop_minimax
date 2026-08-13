# Load keys from G:\private\.env into THIS process only (Load-MinimaxKey.ps1
# never prints, returns, or persists the value).
. $PSScriptRoot\Load-MinimaxKey.ps1

$regPath = "HKCU:\\SOFTWARE\\Policies\\Claude"
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }

Set-ItemProperty -Path $regPath -Name "inferenceProvider" -Value "gateway" -Type String
# Proxy mode: Claude Desktop talks to the local proxy on port 48217.
# The proxy rewrites Anthropic model names to MiniMax-M3 and forwards to
# https://api.minimax.io/anthropic/v1/messages unchanged.
Set-ItemProperty -Path $regPath -Name "inferenceGatewayBaseUrl" -Value "http://127.0.0.1:48217/anthropic" -Type String
# PLACEHOLDER: Claude Desktop requires a non-empty value here, but the proxy
# ignores what Claude sends and always uses the key from G:\private\.env.
# Never write the real key to the registry -- it would be plaintext on disk.
Set-ItemProperty -Path $regPath -Name "inferenceGatewayApiKey" -Value "proxy-managed" -Type String
Set-ItemProperty -Path $regPath -Name "inferenceGatewayAuthScheme" -Value "x-api-key" -Type String
Set-ItemProperty -Path $regPath -Name "modelDiscoveryEnabled" -Value "true" -Type String
# Three picker slots, each routed by the proxy to a different MiniMax model:
#   sonnet -> MiniMax-M3 (multimodal: text+image+video, 1M context)
#   opus   -> MiniMax-M2.7 (text + tools only)
#   haiku  -> MiniMax-M2.1 (text + tools only, faster)
Set-ItemProperty -Path $regPath -Name "inferenceModels" -Value '[{"name":"claude-sonnet-4-5","anthropicFamilyTier":"sonnet","supports1m":true},{"name":"claude-opus-4-6","anthropicFamilyTier":"opus"},{"name":"claude-haiku-4-5","anthropicFamilyTier":"haiku"}]' -Type String
Remove-ItemProperty -Path $regPath -Name "unstableDisableModelVerification" -ErrorAction SilentlyContinue

# Local stdio MCP servers, always available in every chat:
#   hermes3d-locks / hp-mha-serena -> HermesProof multi-agent coordination + Serena semantic tools
#   minimax-media                  -> MiniMax voice (T2A), image, and video generation tools
$githubRoot = Split-Path -Parent $PSScriptRoot
$hermesProofRoot = Join-Path $githubRoot "hermes3d-mcp-lock-orchestrator"
$nodeCommand = (Get-Command node.exe -ErrorAction Stop).Source
$minimaxLauncher = Join-Path $githubRoot "Testing-Claude-Minimax-Mcp\minimax-mcp-server\Start-MinimaxMediaMcp.ps1"

foreach ($requiredPath in @(
    (Join-Path $hermesProofRoot "src\server.mjs"),
    (Join-Path $hermesProofRoot "src\hp-mha-serena\server.mjs"),
    $minimaxLauncher
)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required MCP entry point is missing: $requiredPath"
    }
}

$managedMcpServers = @(
    @{
        name = "hermes3d-locks"
        transport = "stdio"
        command = $nodeCommand
        args = @((Join-Path $hermesProofRoot "src\server.mjs"))
        env = @{ MCP_LOCK_WORKSPACE = $PSScriptRoot }
        toolPolicy = @{ "*" = "allow" }
    },
    @{
        name = "hp-mha-serena"
        transport = "stdio"
        command = $nodeCommand
        args = @((Join-Path $hermesProofRoot "src\hp-mha-serena\server.mjs"))
        env = @{
            MCP_LOCK_WORKSPACE = $PSScriptRoot
            HERMES_WORKSPACE_ROOT = $PSScriptRoot
        }
        toolPolicy = @{ "*" = "allow" }
    },
    @{
        name = "minimax-media"
        transport = "stdio"
        command = "powershell.exe"
        args = @(
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $minimaxLauncher
        )
        toolPolicy = @{ "*" = "allow" }
    }
) | ConvertTo-Json -Depth 10 -Compress
Set-ItemProperty -Path $regPath -Name "managedMcpServers" -Value $managedMcpServers -Type String
Set-ItemProperty -Path $regPath -Name "isLocalDevMcpEnabled" -Value "true" -Type String

Write-Host "Claude Desktop 3P gateway configured. Restart Claude Desktop." -ForegroundColor Green
