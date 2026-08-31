# Explicit dependency installation only; no service or client autostart.
[CmdletBinding(SupportsShouldProcess = $true)]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root 'scripts\Install-Dependencies.ps1') -WhatIf:$WhatIfPreference
Write-Output 'Read README.md for private credentials, service setup and native acceptance. Nothing was auto-started.'
