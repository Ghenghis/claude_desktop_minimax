# Manual UI fixture launcher. Its console is hidden; the test form is visible.
# No watchdog, retry, service, process cleanup, or file changes.
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.Arguments = '-NoProfile -STA -File "' + (Join-Path $PSScriptRoot 'windows_test_fixture.ps1') + '"'
$process = [Diagnostics.Process]::Start($info)
Write-Output ('Opened the disposable Claude MCP test fixture. Close its window when finished. Process: ' + $process.Id)
$process.Dispose()
