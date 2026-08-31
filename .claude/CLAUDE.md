# Project charter

Read AGENTS.md, README.md and .claude/principles.md before changes.
The watchdog and health runner are retired. Do not recreate them.

The stock Claude Desktop app owns coding tasks and MCP lifecycle. The two local
gateways translate authenticated HTTP only. They cannot execute tools.
Use scripts/Gateway-Service.ps1 only for an explicitly requested lifecycle
action. Never touch another application's service or process.

Before declaring completion: run `python scripts/verify.py` and
`python -m unittest discover -s tests -v`; update .claude/notes.md with evidence.
For client acceptance use docs/CLAUDE_ACCEPTANCE.md in a disposable project.
Do not scan dependency directories or all user projects as a verification step.
