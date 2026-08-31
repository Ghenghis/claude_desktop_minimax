# Explicit install only. No application/service launch, scheduled tasks or upgrades on connect.
[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$Python = 'python.exe')
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 is required.' }
$root = Split-Path -Parent $PSScriptRoot
function Invoke-InstallCommand {
    param([string]$Executable, [string[]]$Arguments, [string]$Directory)
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Executable
    $info.WorkingDirectory = $Directory
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($info)
    try {
        $outputTask = $process.StandardOutput.ReadToEndAsync()
        $errorTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(180000)) {
            # Only the installer process just created by this function is owned.
            $process.Kill()
            throw 'Dependency installation exceeded three minutes. No apps were restarted.'
        }
        if ($process.ExitCode -ne 0) { throw $errorTask.GetAwaiter().GetResult() }
        Write-Output $outputTask.GetAwaiter().GetResult()
    } finally { $process.Dispose() }
}
if (-not $PSCmdlet.ShouldProcess($root, 'Install locked dependencies into isolated local environments')) { return }
$pythonPath = (Get-Command $Python -ErrorAction Stop).Source
$environments = @{
    gateway = 'requirements-gateway.lock'
    test = 'requirements-test.lock'
    'windows-mcp' = 'mcp-runtime\windows-mcp-requirements.lock'
    'minimax-plan' = 'mcp-runtime\minimax-plan-requirements.lock'
    'minimax-mcp' = 'mcp-runtime\minimax-mcp-requirements.lock'
}
foreach ($name in $environments.Keys) {
    $destination = Join-Path $root ('venvs\' + $name)
    $executable = Join-Path $destination 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $executable)) {
        Invoke-InstallCommand $pythonPath @('-m','venv',$destination) $root
    }
    Invoke-InstallCommand $executable @('-m','pip','install','--disable-pip-version-check','-r',(Join-Path $root $environments[$name])) $root
}
$node = (Get-Command node.exe -ErrorAction Stop).Source
$npm = Join-Path (Split-Path -Parent $node) 'node_modules\npm\bin\npm-cli.js'
if (-not(Test-Path -LiteralPath $npm)) { throw 'Install Node.js with npm before running this installer.' }
Invoke-InstallCommand $node @($npm,'ci','--ignore-scripts','--no-audit','--no-fund') (Join-Path $root 'mcp-runtime')
Write-Output 'Dependencies ready. No client or gateway was started.'
