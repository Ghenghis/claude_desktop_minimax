# Compatibility entry point. No placeholder credentials or model-list reset.
[CmdletBinding(SupportsShouldProcess=$true)]
param([ValidateRange(1,65535)][int]$ProxyPort=48217)
& (Join-Path $PSScriptRoot 'Set-ClaudeDesktopGateway.ps1') -ProxyPort $ProxyPort -WhatIf:$WhatIfPreference
