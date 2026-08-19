# Wire Claude Desktop to the local MiniMax proxy.
# Writes HKCU:\SOFTWARE\Policies\Claude so the next Claude Desktop launch
# uses the V2 gateway as its Third-Party Inference provider.
# Does NOT touch the MCP server config.

[CmdletBinding()]
param(
    [int]$ProxyPort = 0
)

$ErrorActionPreference = 'Stop'

# Load the MiniMax key into THIS process only (never echoed).
. $PSScriptRoot\Load-MinimaxKey.ps1

$githubRoot = Split-Path -Parent $PSScriptRoot
$portFile = Join-Path $githubRoot 'claude-minimax-v2\.port'

$port = if ($ProxyPort -gt 0) { $ProxyPort } elseif (Test-Path $portFile) {
    [int](Get-Content -Path $portFile -TotalCount 1)
} else { 48217 }

$regPath = 'HKCU:\SOFTWARE\Policies\Claude'
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }

Set-ItemProperty -Path $regPath -Name 'inferenceProvider' -Value 'gateway' -Type String
Set-ItemProperty -Path $regPath -Name 'inferenceGatewayBaseUrl' -Value "http://127.0.0.1:$port/anthropic" -Type String
# Placeholder - the proxy ignores this and uses G:\private\.env directly.
Set-ItemProperty -Path $regPath -Name 'inferenceGatewayApiKey' -Value 'proxy-managed' -Type String
Set-ItemProperty -Path $regPath -Name 'inferenceGatewayAuthScheme' -Value 'x-api-key' -Type String
Set-ItemProperty -Path $regPath -Name 'modelDiscoveryEnabled' -Value 'true' -Type String
$models = @(
    @{ name='claude-sonnet-4-5'; labelOverride='MiniMax M3'; anthropicFamilyTier='sonnet'; supports1m=$true; isFamilyDefault=$true },
    @{ name='claude-opus-4-6'; labelOverride='MiniMax M2.7'; anthropicFamilyTier='opus'; isFamilyDefault=$true },
    @{ name='claude-haiku-4-5'; labelOverride='MiniMax M2.7 Highspeed'; anthropicFamilyTier='haiku'; isFamilyDefault=$true },
    @{ name='claude-sonnet-4'; labelOverride='MiniMax M3 (legacy)'; anthropicFamilyTier='sonnet'; supports1m=$true },
    @{ name='claude-opus-4'; labelOverride='MiniMax M2.7 (legacy)'; anthropicFamilyTier='opus' },
    @{ name='claude-haiku-4'; labelOverride='MiniMax M2.7 Highspeed (legacy)'; anthropicFamilyTier='haiku' }
) | ConvertTo-Json -Depth 10 -Compress
Set-ItemProperty -Path $regPath -Name 'inferenceModels' -Value $models -Type String

Write-Host 'Claude Desktop inference registry wired to MiniMax proxy.' -ForegroundColor Green
Write-Host 'Restart Claude Desktop to pick up the new gateway.' -ForegroundColor Yellow
Get-ItemProperty -Path $regPath |
    Select-Object inferenceProvider,inferenceGatewayBaseUrl,inferenceGatewayAuthScheme,inferenceGatewayApiKey,modelDiscoveryEnabled |
    Format-List
