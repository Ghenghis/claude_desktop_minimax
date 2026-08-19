# Load a GitLab token from S:\private or G:\private and set it for glab / Hermes.
# Place one of these files (plain text, one line, no quotes):
#   S:\private\glab_token.txt
#   G:\private\glab_token.txt
#   S:\private\gitlab_token.txt
#   G:\private\gitlab_token.txt
#
# The token is never displayed or logged.

$ErrorActionPreference = 'Stop'

$candidates = @(
    'S:\private\glab_token.txt',
    'G:\private\glab_token.txt',
    'S:\private\gitlab_token.txt',
    'G:\private\gitlab_token.txt'
)

$token = $null
$source = $null

foreach ($path in $candidates) {
    if (Test-Path -LiteralPath $path) {
        $token = (Get-Content -LiteralPath $path -Raw).Trim()
        $source = $path
        if ($token) { break }
    }
}

if (-not $token) {
    throw "No GitLab token found. Place it in S:\private\glab_token.txt or G:\private\glab_token.txt"
}

[Environment]::SetEnvironmentVariable('GITLAB_TOKEN', $token, 'User')
[Environment]::SetEnvironmentVariable('GLAB_TOKEN', $token, 'User')
$env:GITLAB_TOKEN = $token
$env:GLAB_TOKEN = $token

Write-Host "GitLab token set from $source" -ForegroundColor Green
Write-Host "Restart your shell or IDE for all tools to pick it up." -ForegroundColor Cyan
