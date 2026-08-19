#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$TokenPath = 'G:\private\.proxy-token',
    [string]$EnvPath = 'G:\private\.env',
    [string]$ProxyPath = 'G:\Github\claude-codex-devin\claude-minimax-proxy.py',
    [string]$PythonPath = 'C:\Python314\python.exe',
    [string]$Port = '48217',
    [string]$RegistryPath = 'HKCU:\SOFTWARE\Policies\Claude'
)

$ErrorActionPreference = 'Stop'

function Test-ProxyToken {
    if (Test-Path -LiteralPath $TokenPath) {
        Write-Output 'TOKEN_EXISTS'
        return
    }
    $dir = Split-Path -Parent $TokenPath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    $token = -join ($bytes | ForEach-Object { $_.ToString('x2') })
    $bytes = $null
    Set-Content -LiteralPath $TokenPath -Value $token -Encoding ASCII -NoNewline
    Write-Output 'TOKEN_CREATED'
}

function Repair-TokenAcl {
    $acl = Get-Acl -LiteralPath $TokenPath
    $acl.SetAccessRuleProtection($true, $false)
    $acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }
    $me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Translate([Security.Principal.NTAccount]).Value
    $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($me, 'Read', 'Allow')))
    $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule('SYSTEM', 'FullControl', 'Allow')))
    Set-Acl -LiteralPath $TokenPath $acl
    Write-Output 'ACL_REPAIRED'
}

function Update-ClaudeRegistry {
    param([string]$Token)
    if (-not (Test-Path $RegistryPath)) {
        New-Item -Path $RegistryPath -Force | Out-Null
    }
    Set-ItemProperty -Path $RegistryPath -Name inferenceProvider -Value gateway
    Set-ItemProperty -Path $RegistryPath -Name inferenceGatewayBaseUrl -Value ('http://127.0.0.1:' + $Port + '/anthropic')
    Set-ItemProperty -Path $RegistryPath -Name inferenceGatewayApiKey -Value $Token
    Set-ItemProperty -Path $RegistryPath -Name inferenceGatewayAuthScheme -Value 'x-api-key'
    Write-Output 'REGISTRY_UPDATED'
}

function Restart-Proxy {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'claude-minimax-proxy' } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Output ('KILLED_PID=' + $_.ProcessId)
        }
    Start-Sleep -Seconds 2
    $env:MINIMAX_ENV_FILE = $EnvPath
    $env:CLAUDE_MINIMAX_PROXY_PORT = $Port
    Start-Process -FilePath $PythonPath -ArgumentList $ProxyPath -WindowStyle Hidden -WorkingDirectory 'G:\Github\claude-codex-devin'
    Start-Sleep -Seconds 4
    Write-Output 'PROXY_STARTED'
}

function Test-Proxy {
    param([string]$Token)
    $headers = @{
        'X-Api-Key' = $Token
        'anthropic-version' = '2023-06-01'
        'Content-Type' = 'application/json'
    }
    $payload = @{
        model = 'claude-haiku-4-5'
        max_tokens = 10
        messages = @(
            @{
                role = 'user'
                content = 'hi'
            }
        )
    }
    $body = $payload | ConvertTo-Json -Compress -Depth 10
    try {
        $resp = Invoke-WebRequest -Uri ('http://127.0.0.1:' + $Port + '/anthropic/v1/messages') -Method POST -Headers $headers -Body $body -TimeoutSec 30 -UseBasicParsing
        Write-Output ('STATUS=' + $resp.StatusCode)
        $c = $resp.Content
        Write-Output ('BODY=' + $c.Substring(0, [Math]::Min(500, $c.Length)))
    } catch {
        Write-Output ('ERROR=' + $_.Exception.Message)
        if ($_.Exception.Response) {
            Write-Output ('HTTP=' + [int]$_.Exception.Response.StatusCode)
            try {
                $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                Write-Output ('RESP_BODY=' + $sr.ReadToEnd())
            } catch {}
        }
    }
}

Test-ProxyToken
Repair-TokenAcl
$token = (Get-Content -LiteralPath $TokenPath -Raw).Trim()
Update-ClaudeRegistry -Token $token
Restart-Proxy
Test-Proxy -Token $token
Write-Output ('TOKEN_LEN=' + $token.Length)
