# Compatibility entry point for the explicit, backed-up core MCP profile.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Workspace, [switch]$Apply, [switch]$SkipRestart, [switch]$Live)
$ErrorActionPreference = 'Stop'
$arguments = @((Join-Path $PSScriptRoot 'configure_claude.py'), '--workspace', $Workspace)
if ($Apply) { $arguments += '--apply' }
& python @arguments
if ($LASTEXITCODE -ne 0) { throw 'MCP profile configuration failed.' }
