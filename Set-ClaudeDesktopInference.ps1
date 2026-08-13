# Wire Claude Desktop to the local MiniMax proxy.
# Writes HKCU:\SOFTWARE\Policies\Claude so the next Claude Desktop launch
# uses http://127.0.0.1:48217/anthropic as its Third-Party Inference gateway.
# Does NOT touch the MCP server config.

$ErrorActionPreference = 'Stop'

# Load the MiniMax key into THIS process only (never echoed).
. $PSScriptRoot\Load-MinimaxKey.ps1

$regPath = 'HKCU:\SOFTWARE\Policies\Claude'
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }

Set-ItemProperty -Path $regPath -Name 'inferenceProvider' -Value 'gateway' -Type String
Set-ItemProperty -Path $regPath -Name 'inferenceGatewayBaseUrl' -Value 'http://127.0.0.1:48217/anthropic' -Type String
# Placeholder - the proxy ignores this and uses G:\private\.env directly.
Set-ItemProperty -Path $regPath -Name 'inferenceGatewayApiKey' -Value 'proxy-managed' -Type String
Set-ItemProperty -Path $regPath -Name 'inferenceGatewayAuthScheme' -Value 'x-api-key' -Type String
Set-ItemProperty -Path $regPath -Name 'modelDiscoveryEnabled' -Value 'true' -Type String
Set-ItemProperty -Path $regPath -Name 'inferenceModels' -Value '[{"name":"claude-sonnet-4-5","anthropicFamilyTier":"sonnet","supports1m":true},{"name":"claude-opus-4-6","anthropicFamilyTier":"opus"},{"name":"claude-haiku-4-5","anthropicFamilyTier":"haiku"}]' -Type String

Write-Host 'Claude Desktop inference registry wired to MiniMax proxy.' -ForegroundColor Green
Write-Host 'Restart Claude Desktop to pick up the new gateway.' -ForegroundColor Yellow
Get-ItemProperty -Path $regPath |
    Select-Object inferenceProvider,inferenceGatewayBaseUrl,inferenceGatewayAuthScheme,inferenceGatewayApiKey,modelDiscoveryEnabled |
    Format-List
