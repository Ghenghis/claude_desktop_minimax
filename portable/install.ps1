# Portable installation checks for Claude Desktop  MiniMax V2.
# This runs from start-here.bat before the actual Start-ClaudeMinimaxV2.ps1.
[CmdletBinding()]
param(
    [string]$PrivateRoot = 'G:\private'
)

$ErrorActionPreference = 'Stop'

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host '--- Claude-Desktop MiniMax V2 Portable Installer ---' -ForegroundColor Cyan

# 1. Python check
if (-not (Test-Command 'python')) {
    throw "Python is not on the PATH. Please install Python 3.11+ from https://python.org and re-run start-here.bat."
}
$pyVersion = python --version 2>&1
Write-Host "Python found: $pyVersion" -ForegroundColor Green

# 2. Python compile check for the bundled gateway
$bundleRoot = Split-Path -Parent $PSScriptRoot
$gatewayRoot = Join-Path (Split-Path -Parent $bundleRoot) 'claude-minimax-v2'
if (-not (Test-Path $gatewayRoot -PathType Container)) {
    throw "claude-minimax-v2 gateway not found next to this installer: $gatewayRoot"
}
$pyFiles = Get-ChildItem -Path $gatewayRoot -Recurse -File -Filter '*.py'
foreach ($file in $pyFiles) {
    python -m py_compile $file.FullName
}
Write-Host "All gateway Python files compile." -ForegroundColor Green

# 3. Private key check
$privateDrives = @('S:\private', 'G:\private', 'C:\private') | Where-Object { Test-Path $_ -PathType Container }
$found = $privateDrives | Where-Object {
    (Test-Path (Join-Path $_ 'minimax_key.txt')) -or (Test-Path (Join-Path $_ '.env'))
}
if (-not $found) {
    Write-Host "No MiniMax key found in any of S:\private, G:\private, C:\private." -ForegroundColor Red
    New-Item -ItemType Directory -Path $PrivateRoot -Force | Out-Null
    throw "Place your MiniMax API key in $PrivateRoot\minimax_key.txt (plain text, one line) and run start-here.bat again."
}
Write-Host "MiniMax key found in: $found" -ForegroundColor Green

Write-Host '--- Installer checks passed ---' -ForegroundColor Green
