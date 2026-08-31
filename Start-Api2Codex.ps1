# Explicit start of the owned gateway; does not import arbitrary .env variables.
[CmdletBinding(SupportsShouldProcess=$true)]
param()
& (Join-Path $PSScriptRoot 'scripts/Gateway-Service.ps1') -Action Start -Gateway Codex -WhatIf:$WhatIfPreference
