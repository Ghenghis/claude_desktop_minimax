[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$BackupDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'AICE_DATA\disabled-tasks'))
$ErrorActionPreference = 'Stop'
$names = @('ClaudeMiniMaxProxyWatchdog', 'Watch-ClaudeMiniMaxProxy', 'MiniMaxStack-Health', 'MiniMaxStack-Health-Logon', 'DesklineMiniMaxProxy')
foreach ($name in $names) {
    $task = Get-ScheduledTask -TaskName $name -TaskPath '\' -ErrorAction SilentlyContinue
    if (-not $task) { continue }
    $arguments = $task.Actions.Arguments -join ' '
    if ($arguments -notmatch '(?i)(Watch-ClaudeMiniMaxProxy\.ps1|Test-MiniMaxStack\.ps1|claude-minimax-proxy\.py)') {
        Write-Warning "Skipped $name`: action does not match this harness."
        continue
    }
    if ($PSCmdlet.ShouldProcess($name, 'Back up and disable watchdog task (do not terminate child processes)')) {
        New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
        $path = Join-Path $BackupDirectory ($name + '-' + (Get-Date -Format 'yyyyMMddHHmmssfff') + '.xml')
        Export-ScheduledTask -TaskName $name -TaskPath '\' | Set-Content -LiteralPath $path -Encoding UTF8
        Disable-ScheduledTask -TaskName $name -TaskPath '\' -ErrorAction Stop | Select-Object TaskName, State
    }
}
