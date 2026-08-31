# Manual service lifecycle; never kill by name, PID file, or port.
[CmdletBinding(SupportsShouldProcess = $true)]
param([ValidateSet(48217)][int]$PreferredPort = 48217)
& (Join-Path $PSScriptRoot 'scripts\Gateway-Service.ps1') -Action Start -Gateway Claude -WhatIf:$WhatIfPreference
