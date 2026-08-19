# Generate a 256-bit random proxy token for the Admin Gateway (security Gap 1).
#
# Writes the token to G:\private\.proxy-token (mode 0600, owner-only ACL).
# Mirrors Harden-MinimaxEnv.ps1's DACL pattern so the .env and .proxy-token
# files share the same access rules.
#
# The proxy reads this file on startup and validates the X-Proxy-Token header
# against it (constant-time compare) before forwarding any upstream request.
#
# Run interactively from PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Generate-ProxyToken.ps1
#
# Re-running rotates the token (existing Claude Desktop config will stop
# working until you update inferenceGatewayApiKey with the new SHA-256 hash).
#
# What it does NOT do:
#   - Touch the MiniMax API key
#   - Touch the .env file
#   - Touch Claude Desktop registry keys (run Set-ClaudeDesktopGateway.ps1 after)

[CmdletBinding()]
param(
    [string]$Path = 'G:\private\.proxy-token'
)

$ErrorActionPreference = 'Stop'

# Generate 256 bits (32 bytes) of crypto-random hex.
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $rng.GetBytes($bytes)
} finally {
    $rng.Dispose()
}
$token = -join ($bytes | ForEach-Object { $_.ToString('x2') })
$bytes = $null  # best-effort scrub from memory

$dir = Split-Path -Parent $Path
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Set-Content -LiteralPath $Path -Value $token -Encoding ASCII -NoNewline

# ACL: owner-only read (matches Harden-MinimaxEnv.ps1 pattern).
$acl = Get-Acl -LiteralPath $Path
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }

$me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Translate([Security.Principal.NTAccount]).Value
$allowMe = New-Object System.Security.AccessControl.FileSystemAccessRule($me, 'Read', 'Allow')
$allowSys = New-Object System.Security.AccessControl.FileSystemAccessRule('SYSTEM', 'FullControl', 'Allow')
$denyAll = New-Object System.Security.AccessControl.FileSystemAccessRule('Everyone', 'FullControl', 'Deny')
$acl.AddAccessRule($allowMe)
$acl.AddAccessRule($allowSys)
$acl.AddAccessRule($denyAll)
Set-Acl -LiteralPath $Path $acl

# Compute SHA-256 hash for the registry value Claude Desktop will read.
$hash = [System.Security.Cryptography.SHA256]::Create()
try {
    $hashBytes = $hash.ComputeHash([System.Text.Encoding]::ASCII.GetBytes($token))
    $hashHex = -join ($hashBytes | ForEach-Object { $_.ToString('x2') })
} finally {
    $hash.Dispose()
}

Write-Host "Generated proxy token at $Path" -ForegroundColor Green
Write-Host "SHA-256 (for inferenceGatewayApiKey registry value):" -ForegroundColor Cyan
Write-Host "  $hashHex" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run Set-ClaudeDesktopGateway.ps1 -TokenHash '$hashHex'" -ForegroundColor Yellow
Write-Host "     (or update HKCU:\SOFTWARE\Policies\Claude\inferenceGatewayApiKey manually)" -ForegroundColor Yellow
Write-Host "  2. Restart Claude Desktop" -ForegroundColor Yellow
Write-Host "  3. The proxy will now require X-Proxy-Token on every POST request" -ForegroundColor Yellow

# Optional: emit the literal token so it can be piped to a clipboard / config tool.
# NOTE: this is the ONLY place the raw token is displayed. Treat it like a password.
Write-Host ""
Write-Host "Raw token (copy to Claude Desktop auth provider if needed):" -ForegroundColor DarkGray
Write-Host "  $token" -ForegroundColor DarkGray