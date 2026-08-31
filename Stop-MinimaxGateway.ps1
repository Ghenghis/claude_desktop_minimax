# Manual service lifecycle; never kill by name, PID file, or port.
[CmdletBinding(SupportsShouldProcess = $true)]
param([ValidateSet(48217)][int]$Port = 48217, [int]$TimeoutSeconds = 5)
& (Join-Path $PSScriptRoot 'scripts\Gateway-Service.ps1') -Action Stop -Gateway Claude -WhatIf:$WhatIfPreference
