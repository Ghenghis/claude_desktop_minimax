# Source-only package. No recursive copying/deletion or runtime/private data.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& python (Join-Path $root 'scripts\build_release.py') --output $OutputPath
if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed.' }
