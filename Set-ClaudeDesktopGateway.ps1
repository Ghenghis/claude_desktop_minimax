# Explicit gateway configuration only. Preserve all MCP and picker settings.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateRange(1, 65535)][int]$ProxyPort = 48217,
    [string]$TokenPath = 'C:\private\.proxy-token',
    [string]$GithubRoot = ''
)
$ErrorActionPreference = 'Stop'
$token = [IO.File]::ReadAllText($TokenPath).Trim()
if ($token.Length -lt 32 -or $token -match '\s') { throw 'A valid private gateway token is required; no settings changed.' }
$regPath = 'HKCU:\SOFTWARE\Policies\Claude'
if (Test-Path 'HKLM:\SOFTWARE\Policies\Claude') { $regPath = 'HKLM:\SOFTWARE\Policies\Claude' }
if ($PSCmdlet.ShouldProcess($regPath, 'Configure gateway using local token; preserve MCP settings')) {
    if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
    $settings = @{
        inferenceProvider = 'gateway'
        inferenceGatewayBaseUrl = "http://127.0.0.1:$ProxyPort/anthropic"
        inferenceGatewayApiKey = $token
        inferenceGatewayAuthScheme = 'x-api-key'
    }
    $before = @{}
    $registry = Get-Item -LiteralPath $regPath
    foreach ($name in $settings.Keys) { $before[$name] = $registry.GetValue($name, $null) }
    $backupDir = Join-Path $env:LOCALAPPDATA ('Claude-3p\minimax-profile-backups\' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backupDir 'gateway-connection.json') -Encoding UTF8
    try {
        foreach ($name in $settings.Keys) {
            Set-ItemProperty -Path $regPath -Name $name -Value $settings[$name] -Type String
        }
    } catch {
        foreach ($name in $settings.Keys) {
            if ($null -eq $before[$name]) { Remove-ItemProperty -LiteralPath $regPath -Name $name -ErrorAction SilentlyContinue }
            else { Set-ItemProperty -LiteralPath $regPath -Name $name -Value $before[$name] -Type String }
        }
        throw
    }
    Write-Output 'Gateway configured. All model picker and MCP settings preserved. No app was stopped.'
}
$token = $null
