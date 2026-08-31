## Problem and change

Explain the user-visible problem, the change, and the resulting behavior.

## Verification

- [ ] Offline Python contracts, source verifier, and Node schema tests pass.
- [ ] Affected native-client workflows have observed results, not just handshakes.
- [ ] Failure, cancellation, overload and resource limits remain bounded.
- [ ] No secrets, private logs, environments, or unrelated edits are published.
- [ ] Documentation and release-manifest.json reflect the reviewed files.

## Safety and limitations

State what was not tested and any migration risks. Preserve native approvals.
Never restore watchdogs, automatic repairs, scheduled health checks, process-name
kills, port-owner kills, blanket permission changes, or billed-request retries.
Watch-ClaudeMiniMaxProxy.ps1 and Test-MiniMaxStack.ps1 are retired no-ops, not tests.
