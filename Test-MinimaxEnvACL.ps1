# One-shot metadata check only. No secret contents are read.
[CmdletBinding()]
param([string]$Path='C:\private\.env')
$ErrorActionPreference='Stop'
$acl=Get-Acl -LiteralPath $Path
$allowed=@('S-1-5-18','S-1-5-32-544',[Security.Principal.WindowsIdentity]::GetCurrent().User.Value)
if(-not $acl.AreAccessRulesProtected){throw 'Credential file still inherits access rules.'}
foreach($rule in $acl.Access){
    $sid=$rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
    if($rule.AccessControlType -ne 'Allow' -or $sid -notin $allowed){throw 'Unexpected access rule; no changes were made.'}
}
Write-Output 'Credential ACL allows only current user, SYSTEM and Administrators.'
