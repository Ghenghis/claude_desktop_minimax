# Generate a local bearer secret without displaying it or rotating it implicitly.
[CmdletBinding(SupportsShouldProcess=$true)]
param([string]$Path='C:\private\.proxy-token',[switch]$Rotate)
$ErrorActionPreference='Stop'
if ((Test-Path -LiteralPath $Path) -and -not $Rotate) {
    Write-Output 'Existing token preserved. Explicit -Rotate is required to replace it.'
    return
}
if (Test-Path -LiteralPath $Path) {
    $item=Get-Item -LiteralPath $Path
    if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Expected a regular token file.'}
}
if (-not $PSCmdlet.ShouldProcess($Path,'Create private local gateway token; active client credentials must be updated after rotation')) { return }
$parent=Split-Path -Parent ([IO.Path]::GetFullPath($Path))
if(-not(Test-Path -LiteralPath $parent)){New-Item -ItemType Directory -Path $parent | Out-Null}
if(-not(Test-Path -LiteralPath $Path)){[IO.File]::WriteAllText($Path,'')}
& (Join-Path (Split-Path -Parent $PSScriptRoot) 'Harden-MinimaxEnv.ps1') -Path $Path
$bytes=New-Object byte[] 32
$rng=[Security.Cryptography.RandomNumberGenerator]::Create()
try{$rng.GetBytes($bytes)}finally{$rng.Dispose()}
$token=-join($bytes|ForEach-Object{$_.ToString('x2')})
[IO.File]::WriteAllText($Path,$token)
[Array]::Clear($bytes,0,$bytes.Length)
$token=$null
Write-Output 'Token saved privately. Run Set-ClaudeDesktopGateway.ps1 and deploy the gateways explicitly. No apps were restarted.'
