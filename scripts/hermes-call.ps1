# hermes-call.ps1 — Helper for skills to record evidence via HermesProof MCP.
#
# Wraps the standard 6-step trace pattern from .harness/HARNESS.md:
#   1. hermes_anonymous_claim  role=<role>  ttl_minutes=<n>
#   2. (optional) hermes_lock_files <files>
#   3. <do the work>
#   4. hermes_append_evidence  kind=<skill_name>  summary=<text>
#   5. hermes_record_outcome  <merge|lgtm|timeout|reject>
#   6. hermes_anonymous_release  role=<role>
#
# Usage (from a Skill or sub-agent):
#   scripts/hermes-call.ps1 trace -skill watchdog-self-test -summary "PASS restart in 8s"
#   scripts/hermes-call.ps1 claim -role BUILDER -ttl_minutes 10
#   scripts/hermes-call.ps1 evidence -kind proxy-cache-tune -summary "TTL bumped 24h -> 48h"
#   scripts/hermes-call.ps1 outcome merge
#   scripts/hermes-call.ps1 release -role BUILDER
#
# What it does NOT do:
#   - Call the MCP tool directly (the agent invokes the hermes3d-locks tool).
#     This script EMITS the canonical invocation sequence so skills can do
#     one bash call instead of N.
#   - Touch the registry, env vars, or any file outside AICE_DATA/.

[CmdletBinding()]
param(
    [Parameter(Position=0)] [string]$Action = "trace",
    [string]$Skill = "",
    [string]$Role = "BUILDER",
    [int]$TtlMinutes = 10,
    [string]$Summary = "",
    [ValidateSet("merge","lgtm","timeout","reject")] [string]$Outcome = "merge",
    [string[]]$Files = @()
)

$ErrorActionPreference = 'Stop'

# HermesProof tool invocations are made by the agent through the
# hermes3d-locks MCP server. This script just prints the canonical
# invocation sequence so it can be copied or executed by the agent.
# When the hermes3d-locks tools are exposed to the agent's tool belt,
# the agent substitutes these prints for the actual tool calls.

function Write-Invocation {
    param([string]$Tool, [hashtable]$Args)
    $argStr = ($Args.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ' '
    Write-Output "hermes_call $Tool $argStr"
}

switch ($Action) {
    "claim" {
        Write-Invocation "hermes_anonymous_claim" @{
            role=$Role; ttl_minutes=$TtlMinutes
        }
    }
    "lock" {
        if (-not $Files) { throw "lock requires -Files" }
        Write-Invocation "hermes_lock_files" @{ files=($Files -join ",") }
    }
    "evidence" {
        if (-not $Skill)  { throw "evidence requires -Skill" }
        if (-not $Summary) { throw "evidence requires -Summary" }
        Write-Invocation "hermes_append_evidence" @{
            kind=$Skill
            summary=$Summary
            data_json='{"harness":"admin-gateway-v0.1.1"}'
        }
    }
    "outcome" {
        Write-Invocation "hermes_record_outcome" @{ outcome=$Outcome }
    }
    "release" {
        Write-Invocation "hermes_anonymous_release" @{ role=$Role }
    }
    "trace" {
        # Full 6-step sequence for a one-shot skill invocation
        if (-not $Skill)  { throw "trace requires -Skill" }
        if (-not $Summary) { throw "trace requires -Summary" }
        Write-Invocation "hermes_anonymous_claim" @{ role=$Role; ttl_minutes=$TtlMinutes }
        if ($Files) {
            Write-Invocation "hermes_lock_files" @{ files=($Files -join ",") }
        }
        Write-Invocation "hermes_append_evidence" @{
            kind=$Skill; summary=$Summary
            data_json='{"harness":"admin-gateway-v0.1.1"}'
        }
        Write-Invocation "hermes_record_outcome" @{ outcome=$Outcome }
        Write-Invocation "hermes_anonymous_release" @{ role=$Role }
    }
    default {
        Write-Error "Unknown action: $Action. Use: claim|lock|evidence|outcome|release|trace"
    }
}