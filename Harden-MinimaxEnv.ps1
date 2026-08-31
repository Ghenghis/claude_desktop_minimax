# Explicitly protect one credential file. Never add a deny-Everyone ACE.
[CmdletBinding(SupportsShouldProcess=$true)]
param([string]$Path='C:\private\.env')
$ErrorActionPreference='Stop'
$item=Get-Item -LiteralPath $Path -ErrorAction Stop
if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Expected a regular credential file.' }
if (-not $PSCmdlet.ShouldProcess($item.FullName,'Restrict credential ACL to current user, SYSTEM and Administrators')) { return }
$acl=Get-Acl -LiteralPath $item.FullName
$backup=$item.FullName+'.acl-'+[Guid]::NewGuid().ToString('N')
[IO.File]::WriteAllText($backup,$acl.Sddl)
$acl.SetAccessRuleProtection($true,$false)
foreach($rule in @($acl.Access)){[void]$acl.RemoveAccessRuleSpecific($rule)}
$user=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach($sidText in @('S-1-5-18','S-1-5-32-544',$user)){
    $sid=[Security.Principal.SecurityIdentifier]::new($sidText)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','Allow'))
}
Set-Acl -LiteralPath $item.FullName -AclObject $acl
Write-Output "Protected credential file. Previous ACL saved at $backup"
