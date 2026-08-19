# DAVE-AI preflight - safe version that avoids known blocking calls.
# Skips Get-WindowsOptionalFeature (often slow/needs admin) and suppresses console noise.
[CmdletBinding()]
param(
    [string]$OutFile = ".\DAVEAI-preflight.json"
)

$ErrorActionPreference = "SilentlyContinue"

function Test-ToolPresence([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction Ignore
    if (-not $cmd) {
        return [ordered]@{ name=$Name; found=$false; path=$null }
    }
    return [ordered]@{ name=$Name; found=$true; path=$cmd.Source }
}

$tools = @(
    (Test-ToolPresence "git"),
    (Test-ToolPresence "node"),
    (Test-ToolPresence "npm"),
    (Test-ToolPresence "npx"),
    (Test-ToolPresence "python"),
    (Test-ToolPresence "py"),
    (Test-ToolPresence "java"),
    (Test-ToolPresence "pwsh"),
    (Test-ToolPresence "winget"),
    (Test-ToolPresence "docker"),
    (Test-ToolPresence "claude"),
    (Test-ToolPresence "uv"),
    (Test-ToolPresence "serena"),
    (Test-ToolPresence "adb"),
    (Test-ToolPresence "scrcpy"),
    (Test-ToolPresence "ffmpeg"),
    (Test-ToolPresence "maestro"),
    (Test-ToolPresence "jadx"),
    (Test-ToolPresence "jadx_mcp_server"),
    (Test-ToolPresence "r2"),
    (Test-ToolPresence "r2pm"),
    (Test-ToolPresence "x64dbg-automate-mcp"),
    (Test-ToolPresence "winapp"),
    (Test-ToolPresence "playwright-cli"),
    (Test-ToolPresence "ghidraRun"),
    (Test-ToolPresence "apktool"),
    (Test-ToolPresence "AssetRipper"),
    (Test-ToolPresence "Cpp2IL"),
    (Test-ToolPresence "dnSpyEx"),
    (Test-ToolPresence "ghidra"),
    (Test-ToolPresence "r2frida")
)

$report = [ordered]@{
    generated = (Get-Date).ToString("o")
    machine = $env:COMPUTERNAME
    os = [System.Environment]::OSVersion.VersionString
    tools = $tools
    adb_devices = $null
    notes = @(
        "This checker is read-only except for writing this report.",
        "A found executable does not prove its MCP server is configured; smoke-test each active profile separately.",
        "Missing optional tools are not failures. Install only what the selected profile requires.",
        "Safe preflight skipped Hyper-V optional feature check because it requires elevation and can hang."
    )
}

$report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $OutFile
Write-Output "Preflight report written to: $OutFile"
