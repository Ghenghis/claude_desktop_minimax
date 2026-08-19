# Tighten ACL on G:\private\.env -- current user only, deny everyone else.
# Must be run elevated (Admin) because the file is currently owned by
# BUILTIN\Administrators and grants modify to Authenticated Users.
#
# Run interactively from an elevated PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File G:\Github\claude-codex-devin\Harden-MinimaxEnv.ps1

$ErrorActionPreference = 'Stop'
$envPath = 'G:\private\.env'

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing $envPath"
}

# Take ownership if not already owned by us.
$acl = Get-Acl -LiteralPath $envPath
$me  = [Security.Principal.WindowsIdentity]::GetCurrent().User
$currentOwner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
if ($currentOwner -ne $me.Value) {
    Write-Host "Taking ownership..." -ForegroundColor Yellow
    & takeown.exe "/F" "$envPath"
    $acl = Get-Acl -LiteralPath $envPath
}

# Disable inheritance, keep explicit rules, then strip everything except us + SYSTEM.
$acl.SetAccessRuleProtection($true, $false)

# Wipe and rebuild explicit access.
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }

$meAcct = $env:USERNAME
$allowMe = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $meAcct, 'Read', 'Allow')
$allowSys = New-Object System.Security.AccessControl.FileSystemAccessRule(
    'SYSTEM', 'FullControl', 'Allow')
$denyAll = New-Object System.Security.AccessControl.FileSystemAccessRule(
    'Everyone', 'FullControl', 'Deny')

$acl.AddAccessRule($allowMe)
$acl.AddAccessRule($allowSys)
$acl.AddAccessRule($denyAll)
Set-Acl -LiteralPath $envPath $acl

# Set owner explicitly to current user.
$ownerAcct = (Get-CimInstance -ClassName Win32_UserAccount -Filter "Name='$meAcct'").SID
if ($ownerAcct) {
    $sd = New-Object System.Security.AccessControl.SecurityIdentifier($ownerAcct)
    $acl = Get-Acl -LiteralPath $envPath
    $acl.SetOwner($sd)
    Set-Acl -LiteralPath $envPath $acl
}

Write-Host "Done. Re-run Test-MinimaxEnvACL.ps1 to confirm." -ForegroundColor Green