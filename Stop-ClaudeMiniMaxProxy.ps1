# Manual service lifecycle; never kill by name, PID file, or port.
[CmdletBinding(SupportsShouldProcess = $true)]
param()
& (Join-Path $PSScriptRoot 'scripts\Gateway-Service.ps1') -Action Stop -Gateway Claude -WhatIf:$WhatIfPreference
