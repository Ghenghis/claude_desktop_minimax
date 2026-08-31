[CmdletBinding()]
param()
Write-Warning 'Automatic repair is retired. This command only runs a read-only health check.'
& (Join-Path $PSScriptRoot 'Test-MiniMaxStack.ps1')
