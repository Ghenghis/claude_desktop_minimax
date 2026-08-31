# Manual acceptance entry point; never repairs, restarts or schedules anything.
[CmdletBinding()]
param([switch]$Live,[string]$SshAlias='')
$arguments=@((Join-Path $PSScriptRoot 'scripts\Test-ClaudeTools.py'))
if($Live){$arguments+='--live'}
if($SshAlias){$arguments+=@('--ssh-alias',$SshAlias)}
$python = Join-Path $PSScriptRoot 'venvs\test\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Acceptance dependencies are missing. Run scripts\Install-Dependencies.ps1 explicitly first.'
}
& $python @arguments
exit $LASTEXITCODE
