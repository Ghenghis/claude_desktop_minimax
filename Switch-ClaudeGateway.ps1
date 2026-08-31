[CmdletBinding(SupportsShouldProcess=$true)]
param([ValidateSet('LiteLLM','Proxy')][string]$Mode='Proxy')
if ($Mode -eq 'LiteLLM') { throw 'The experimental LiteLLM path is not a supported release profile. No services or settings changed.' }
if ($PSCmdlet.ShouldProcess('Claude connection','Set request-only MiniMax gateway')) {
    & (Join-Path $PSScriptRoot 'Set-ClaudeDesktopGateway.ps1')
}
