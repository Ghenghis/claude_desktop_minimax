# Manual lifecycle only. Never infer ownership from a TCP port or PID file.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Status', 'Start', 'Stop')][string]$Action = 'Status',
    [ValidateSet('Claude', 'Codex')][string]$Gateway = 'Claude'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$name = if ($Gateway -eq 'Claude') { 'claude-minimax-proxy' } else { 'api2codex-minimax' }
$binary = if ($Gateway -eq 'Claude') { 'claude-minimax-proxy-service.exe' } else { 'api2codex-service.exe' }
$expected = [IO.Path]::GetFullPath((Join-Path $root $binary))
$service = Get-CimInstance Win32_Service -Filter "Name='$name'" -ErrorAction Stop
if (-not $service) { throw "Service $name is not installed. No process was started or stopped." }
$actual = $service.PathName.Trim().Trim('"')
$deployed = Join-Path (Join-Path $env:ProgramData 'ClaudeMiniMax') $binary
if ($actual -notin @($expected, $deployed)) {
    throw "Service $name belongs to a different installation ($actual). No action taken."
}
if ($Action -eq 'Start' -and $service.State -ne 'Running' -and $PSCmdlet.ShouldProcess($name, 'Start owned gateway service')) {
    Start-Service -Name $name -ErrorAction Stop
}
if ($Action -eq 'Stop' -and $service.State -ne 'Stopped' -and $PSCmdlet.ShouldProcess($name, 'Stop owned gateway service; active requests will end')) {
    Stop-Service -Name $name -ErrorAction Stop
}
Get-Service -Name $name | Select-Object Name, Status
