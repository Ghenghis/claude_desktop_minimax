# Build a self-contained portable zip for any Windows 11 PC.
# The zip contains claude-codex-devin, claude-minimax-v2, and a top-level start-here.bat.
[CmdletBinding()]
param(
    [string]$OutputPath = 'G:\Github\claude-minimax-v2-portable.zip'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$githubRoot = Split-Path -Parent $repoRoot
$tempRoot = Join-Path $env:TEMP ("claude-minimax-v2-portable-" + [Guid]::NewGuid().ToString())

$sourceCodex = Join-Path $githubRoot 'claude-codex-devin'
$sourceMini = Join-Path $githubRoot 'claude-minimax-v2'
$destCodex = Join-Path $tempRoot 'claude-codex-devin'
$destMini = Join-Path $tempRoot 'claude-minimax-v2'

if (-not (Test-Path $sourceCodex -PathType Container)) { throw "claude-codex-devin not found at $sourceCodex" }
if (-not (Test-Path $sourceMini -PathType Container)) { throw "claude-minimax-v2 not found at $sourceMini" }

# Copy source to temp, skipping .git and other runtime artifacts.
$excludes = @('.git', '.venv', '__pycache__', '*.pyc', '.port', '*.log', '.hermes3d_orchestrator')
function Copy-PortableTree($src, $dst) {
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    Get-ChildItem -Path $src -Force | Where-Object {
        $item = $_
        $excludes | ForEach-Object {
            if ($item.Name -like $_ -or ($_.Attributes -band [System.IO.FileAttributes]::Hidden) -and $item.Name -eq '.git') { return $false }
        }
        return $true
    } | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length + 1)
        $target = Join-Path $dst $rel
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
            Copy-PortableTree -src $_.FullName -dst $target
        } else {
            $parent = Split-Path -Parent $target
            if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
            Copy-Item -Path $_.FullName -Destination $target -Force
        }
    }
}

Copy-PortableTree -src $sourceCodex -dst $destCodex
Copy-PortableTree -src $sourceMini -dst $destMini

# Top-level start-here.bat for the zip
$startHere = @'
@echo off
:: One-click Windows launcher for the Claude-Desktop MiniMax V2 portable bundle.
:: Double-click this file on any Windows 11 PC. It runs the installer and then
:: starts the gateway if the installation checks pass.

echo ******************************************
echo  Claude Desktop  MiniMax V2  Portable
echo ******************************************
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0claude-codex-devin\portable\install.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Setup failed. See the messages above.
    pause
    exit /b %errorlevel%
)

echo.
echo Starting the MiniMax V2 gateway...
powershell -ExecutionPolicy Bypass -File "%~dp0claude-codex-devin\Start-ClaudeMinimaxV2.ps1"

pause
'@
Set-Content -Path (Join-Path $tempRoot 'start-here.bat') -Value $startHere -Encoding ASCII

# Quick-start README for the zip
$readme = @'
# Claude Desktop  MiniMax V2 — Portable

1. Copy this entire folder to the target Windows 11 PC.
2. Place the MiniMax API key in `C:\private\minimax_key.txt` (plain text, one line).
   The installer also accepts `G:\private\minimax_key.txt` or `S:\private\minimax_key.txt`.
3. Double-click `start-here.bat`.
4. When the script says to restart Claude Desktop, close and reopen Claude Desktop.

For issues, run `claude-codex-devin\Repair-ClaudeMinimaxV2.ps1`.
'@
Set-Content -Path (Join-Path $tempRoot 'README-PORTABLE.txt') -Value $readme -Encoding ASCII

# Build the zip.
if (Test-Path $OutputPath) { Remove-Item $OutputPath -Force }
Compress-Archive -Path (Join-Path $tempRoot '*') -DestinationPath $OutputPath -Force

Remove-Item -Path $tempRoot -Recurse -Force

Write-Host "Portable zip built: $OutputPath" -ForegroundColor Green
Write-Host "Extract the zip on a clean Windows 11 PC and run start-here.bat." -ForegroundColor Cyan
