# Retired: never force a client into bypass-permissions mode.
[CmdletBinding()]
param()
Write-Warning 'Permission overrides are retired. Use the native client permission selector for the current task. No settings changed.'
