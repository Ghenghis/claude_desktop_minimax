# Install a working minimax-media MCP server into Windsurf / Devin's mcp_config.json.
[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $env:USERPROFILE 'mcp_config.json')
)

$ErrorActionPreference = 'Stop'

# 1. Find a Python with the mcp package.
$pythonCandidates = @(
    $env:MINIMAX_MCP_PYTHON,
    "C:\Python314\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
) | Where-Object { $_ }

$pythonPath = $null
foreach ($candidate in $pythonCandidates) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    & $candidate -c "from mcp.server.fastmcp import FastMCP" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pythonPath = $candidate
        break
    }
}

if (-not $pythonPath) {
    throw "No Python runtime with the 'mcp' package found. Install pip package 'mcp' first:  pip install mcp==1.28.1"
}

# 2. Resolve the minimax-media server.py relative to this repo.
$serverPath = Join-Path (Split-Path -Parent $PSScriptRoot) '..' 'Testing-Claude-Minimax-Mcp' 'minimax-mcp-server' 'server.py' | Resolve-Path

# 3. Load or create the config.
$config = @{ mcpServers = @{} }
if (Test-Path -LiteralPath $ConfigPath) {
    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json -AsHashtable
    if (-not $config.ContainsKey('mcpServers')) {
        $config.mcpServers = @{}
    }
}

# 4. Add/replace the minimax-media entry.
$config.mcpServers['minimax-media'] = @{
    command = $pythonPath
    args = @($serverPath.Path)
    env = @{
        MCP_TRANSPORT = 'stdio'
        MCP_LOG_LEVEL = 'debug'
        NODE_ENV = 'production'
    }
}

# 5. Write back a clean JSON.
$config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host "Windsurf / Devin MCP config updated: $ConfigPath" -ForegroundColor Green
Write-Host "minimax-media uses: $pythonPath $serverPath" -ForegroundColor Cyan
Write-Host "Restart Windsurf / Devin for the change to take effect." -ForegroundColor Yellow
