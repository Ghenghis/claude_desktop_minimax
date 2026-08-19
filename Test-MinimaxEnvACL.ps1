# Verify MiniMax .env ACL and key presence without exposing the value.
#
# Run:
#   powershell -NoProfile -File G:\Github\claude-codex-devin\Test-MinimaxEnvACL.ps1
#
# What it checks:
#   - File exists at G:\private\.env
#   - Current user can read it
#   - Non-owner users are NOT granted any rights (deny-by-default expected)
#   - The file contains a MINIMAX_API_KEY= line (length only, never the value)
#
# What it NEVER does:
#   - Print, log, or return the API key value
#   - Write to PowerShell history beyond this script's path
#   - Touch the registry or Claude Desktop config

$ErrorActionPreference = 'Stop'

$envPath = 'G:\private\.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "Missing $envPath"
    exit 1
}

$item = Get-Item -LiteralPath $envPath
$acl  = Get-Acl -LiteralPath $envPath

$owner      = $acl.Owner
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().User
$isOwner    = ($owner -eq $currentUser.Value) -or ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -eq $currentUser.Value)

Write-Host ("Path       : {0}" -f $envPath)
Write-Host ("Length     : {0} bytes" -f $item.Length)
Write-Host ("Owner      : {0}" -f $owner)
Write-Host ("Owned by me: {0}" -f $isOwner)

$bad = $acl.Access | Where-Object {
    $_.IdentityReference -ne 'SYSTEM' -and
    $_.IdentityReference -ne $owner -and
    $_.IdentityReference -ne 'BUILTIN\Administrators'
} | Where-Object { $_.FileSystemRights -match 'Read|Modify|FullControl|Write' }

if ($bad) {
    Write-Warning "Non-owner principals have access to $envPath :"
    $bad | ForEach-Object { Write-Warning ("  {0} -> {1}" -f $_.IdentityReference, $_.FileSystemRights) }
} else {
    Write-Host "ACL        : only owner + SYSTEM/Admins (good)" -ForegroundColor Green
}

$line = Select-String -LiteralPath $envPath -Pattern '^MINIMAX_API_KEY\s*=' -ErrorAction SilentlyContinue
if ($line) {
    Write-Host ("Key line   : found, length={0} (value not displayed)" -f $line.Line.Length) -ForegroundColor Green
} else {
    Write-Warning "No MINIMAX_API_KEY= line found in $envPath"
    exit 2
}
