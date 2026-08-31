# Explicit deployment only. No scheduled tasks, recovery actions, app restarts, or port-owner kills.
[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$Activate, [switch]$DownloadWinSW)
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Use PowerShell 7 for service migration.' }
$source = Split-Path -Parent $PSScriptRoot
$installRoot = Join-Path $env:ProgramData 'ClaudeMiniMax'
$pythonPath = Join-Path $source 'venvs\gateway\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts\Install-Dependencies.ps1 first.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Installing service identities requires an administrator terminal. No changes made.'
}
$services = @(
    @{ Name='claude-minimax-proxy'; Binary='claude-minimax-proxy-service.exe'; Script='claude-minimax-proxy.py'; Port='48217' },
    @{ Name='api2codex-minimax'; Binary='api2codex-service.exe'; Script='api2codex.py'; Port='48218' }
)
foreach ($item in $services) {
    $service = Get-CimInstance Win32_Service -Filter "Name='$($item.Name)'"
    if ($service) {
        $actual = $service.PathName.Trim().Trim('"')
        $allowed = @((Join-Path $source $item.Binary), (Join-Path $installRoot $item.Binary))
        if ($actual -notin $allowed) { throw "Service $($item.Name) belongs to another installation. No changes made." }
        if ($service.State -ne 'Stopped' -and -not $Activate) {
            throw 'Gateway is running. Explicitly stop it first, or use -Activate during an idle maintenance window.'
        }
    }
}
if (-not $PSCmdlet.ShouldProcess($installRoot, 'Deploy gateways with separate non-admin service identities and no recovery')) { return }
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
$backup = Join-Path $installRoot ('backups\' + [Guid]::NewGuid().ToString('N'))

function Set-PrivateAcl {
    param([string]$Path, [switch]$ServiceRead)
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleSpecific($rule) }
    foreach ($sidText in @('S-1-5-18','S-1-5-32-544',$identity.User.Value)) {
        $sid = [Security.Principal.SecurityIdentifier]::new($sidText)
        if (Test-Path -LiteralPath $Path -PathType Container) {
            $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
        } else {
            $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'Allow'))
        }
    }
    if ($ServiceRead) {
        foreach ($item in $services) {
            $account = [Security.Principal.NTAccount]::new('NT SERVICE', $item.Name)
            $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($account, 'ReadAndExecute', 'Allow'))
        }
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}
function Invoke-ServiceConfiguration {
    param([string[]]$Parameters)
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = Join-Path $env:WINDIR 'System32\sc.exe'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $Parameters) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($start)
    try {
        $outputTask = $process.StandardOutput.ReadToEndAsync()
        $errorTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(30000)) { throw 'Service configuration timed out.' }
        $output = $outputTask.GetAwaiter().GetResult()
        $errorOutput = $errorTask.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw "Service configuration failed: $output $errorOutput" }
    } finally { $process.Dispose() }
}
# Validate dependencies and credentials before stopping anything. WinSW is a
# pinned official release, never an arbitrary service executable from PATH.
$winSWHash = '05B82D46AD331CC16BDC00DE5C6332C1EF818DF8CEEFCD49C726553209B3A0DA'
$winSWSource = Join-Path $source 'claude-minimax-proxy-service.exe'
if (-not (Test-Path -LiteralPath $winSWSource)) { $winSWSource = Join-Path $installRoot 'claude-minimax-proxy-service.exe' }
if (-not (Test-Path -LiteralPath $winSWSource)) {
    if (-not $DownloadWinSW) { throw 'Use -DownloadWinSW to obtain the pinned official WinSW 2.12.0 binary.' }
    $winSWSource = Join-Path $installRoot 'WinSW-2.12.0-x64.download'
    Invoke-WebRequest -Uri 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe' -OutFile $winSWSource -TimeoutSec 30
}
if ((Get-FileHash -LiteralPath $winSWSource -Algorithm SHA256).Hash -ne $winSWHash) { throw 'WinSW checksum mismatch.' }
$key = $null
foreach ($line in [IO.File]::ReadAllLines('C:\private\.env')) {
    if ($line -match '^\s*(?:export\s+)?MINIMAX_API_KEY\s*=\s*(.+?)\s*$') {
        $key = $Matches[1].Trim().Trim('"').Trim("'")
        break
    }
}
if (-not $key -or $key -match "[\r\n]") { throw 'MiniMax key unavailable; nothing stopped.' }
$token = [IO.File]::ReadAllText('C:\private\.proxy-token').Trim()
if ($token.Length -lt 32 -or $token -match '\s') { throw 'Invalid local gateway token.' }
foreach ($item in $services) {
    $existing = Get-Service -Name $item.Name -ErrorAction SilentlyContinue
    if ($existing) {
        if ($Activate) { Stop-Service -Name $item.Name -ErrorAction Stop }
    } else {
        $futureExe = Join-Path $installRoot $item.Binary
        Invoke-ServiceConfiguration -Parameters @('create', $item.Name, 'binPath=', ('"' + $futureExe + '"'), 'start=', 'demand', 'obj=', ('NT SERVICE\' + $item.Name))
    }
}
# The private directory is restricted before any secrets are copied.
Set-PrivateAcl -Path $installRoot -ServiceRead
# The isolated runtime must be readable by the two restricted service accounts.
# Its files remain unwritable to the services.
$runtimePath = Split-Path -Parent (Split-Path -Parent $pythonPath)
$runtimeAcl = Get-Acl -LiteralPath $runtimePath
foreach ($item in $services) {
    $runtimeAccount = [Security.Principal.NTAccount]::new('NT SERVICE', $item.Name)
    $runtimeAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($runtimeAccount, 'ReadAndExecute', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
}
Set-Acl -LiteralPath $runtimePath -AclObject $runtimeAcl
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Set-PrivateAcl -Path $backup
foreach ($item in $services) {
    Get-CimInstance Win32_Service -Filter "Name='$($item.Name)'" |
        Select-Object Name,PathName,StartName,StartMode | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $backup ($item.Name + '.json')) -Encoding UTF8
}
foreach ($file in @('gateway_common.py','responses_bridge.py','api2codex.py','claude-minimax-proxy.py')) {
    $target = Join-Path $installRoot $file
    if (Test-Path -LiteralPath $target) { Copy-Item -LiteralPath $target -Destination $backup }
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination $target
    Set-PrivateAcl -Path $target -ServiceRead
}
# Give services only the required upstream key, never the entire private .env.
foreach ($name in @('gateway.env','gateway.token')) {
    $path = Join-Path $installRoot $name
    if (-not(Test-Path -LiteralPath $path)) { [IO.File]::WriteAllText($path, '') }
    Set-PrivateAcl -Path $path -ServiceRead
}
[IO.File]::WriteAllText((Join-Path $installRoot 'gateway.env'), "MINIMAX_API_KEY=$key")
[IO.File]::WriteAllText((Join-Path $installRoot 'gateway.token'), $token)
$key = $null
$token = $null
foreach ($item in $services) {
    $exe = Join-Path $installRoot $item.Binary
    if (-not(Test-Path -LiteralPath $exe)) { Copy-Item -LiteralPath $winSWSource -Destination $exe }
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $winSWHash) { throw 'Installed WinSW checksum mismatch.' }
    Set-PrivateAcl -Path $exe -ServiceRead
    $logPath = Join-Path $installRoot ('logs\' + $item.Name)
    New-Item -ItemType Directory -Path $logPath -Force | Out-Null
    Set-PrivateAcl -Path $logPath
    $acl = Get-Acl -LiteralPath $logPath
    $account = [Security.Principal.NTAccount]::new('NT SERVICE', $item.Name)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($account, 'Modify', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    Set-Acl -LiteralPath $logPath -AclObject $acl
    $xmlPath = [IO.Path]::ChangeExtension($exe, '.xml')
    $escape = [Security.SecurityElement]
    $pythonXml = $escape::Escape($pythonPath)
    $scriptXml = $escape::Escape((Join-Path $installRoot $item.Script))
    $rootXml = $escape::Escape($installRoot)
    $logXml = $escape::Escape($logPath)
    @"
<service>
  <id>$($item.Name)</id><name>$($item.Name)</name>
  <executable>$pythonXml</executable><arguments>-B "$scriptXml"</arguments>
  <workingdirectory>$rootXml</workingdirectory>
  <env name="MINIMAX_ENV_FILE" value="$rootXml\gateway.env"/>
  <env name="MINIMAX_PROXY_TOKEN_FILE" value="$rootXml\gateway.token"/>
  <env name="CLAUDE_MINIMAX_PROXY_PORT" value="$($item.Port)"/>
  <env name="PORT" value="$($item.Port)"/>
  <env name="PYTHONNOUSERSITE" value="1"/>
  <startmode>Manual</startmode><onfailure action="none"/><priority>belownormal</priority>
  <serviceaccount><domain>NT SERVICE</domain><user>$($item.Name)</user></serviceaccount>
  <logpath>$logXml</logpath><log mode="roll-by-size"><sizeThreshold>1024</sizeThreshold><keepFiles>3</keepFiles></log>
</service>
"@ | Set-Content -LiteralPath $xmlPath -Encoding UTF8
    Set-PrivateAcl -Path $xmlPath -ServiceRead
    # sc.exe needs a real empty argument; PowerShell 7 preserves it, PS5.1 does not.
    # Use .NET ProcessStartInfo.ArgumentList via PowerShell 7 for unambiguous arguments.
    Invoke-ServiceConfiguration -Parameters @('sidtype', $item.Name, 'restricted')
    Invoke-ServiceConfiguration -Parameters @('privs', $item.Name, 'SeChangeNotifyPrivilege')
    Invoke-ServiceConfiguration -Parameters @('config', $item.Name, 'binPath=', ('"' + $exe + '"'), 'start=', 'demand', 'obj=', ('NT SERVICE\' + $item.Name))
    Invoke-ServiceConfiguration -Parameters @('failure', $item.Name, 'reset=', '86400', 'actions=', '')
}
if ($Activate) { foreach ($item in $services) { Start-Service -Name $item.Name -ErrorAction Stop } }
Write-Output "Gateway deployment complete. Manual start, no recovery; backup: $backup"
