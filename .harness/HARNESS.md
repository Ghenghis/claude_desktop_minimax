# Admin Gateway Harness — Master Contract

This document is the contract that ties together everything in `.harness/`. It is
**always-loaded context** for any agent (Claude Code, MCP server, CI bot, sub-task)
operating in this repo.

## The 7 layers of the harness (HP-MHA spec)

| Layer | Where it lives | What it does |
|---|---|---|
| **Execution** | `claude-minimax-proxy.py` + PowerShell scripts | The stdlib Python proxy + Windows wrappers that run on `127.0.0.1:48217` |
| **Model** | `.harness/contracts/proxy-config.schema.json` `model_map` + `MODEL_CHAINS` in proxy | Picker slot → MiniMax model + waterfall fallback chain |
| **Tools** | `.harness/skills/` + `scripts/` + MCP connectors | Skills are declarative; scripts are imperative; connectors wire external systems |
| **Context** | `.claude/CLAUDE.md` + `.claude/principles.md` + `.claude/notes.md` | Always-loaded project charter + standing rules + persistent notebook |
| **Scheduling** | `Run-StabilitySuite.ps1` + Windows Task Scheduler + GitHub Actions | When each gate runs (manual / daily / nightly / on-PR) |
| **Observability** | `/healthz` + `/readyz` + `AICE_DATA/*.log` + OTel-spans-ready helpers | Live state + log stream + future traces |
| **Verification** | `.claude/verifiers/run.sh` + `tests/test_proxy_e2e.py` + `Test-ClaudeMiniMaxSetup.ps1` | Pre-commit + offline unit + live MiniMax e2e |
| **Governance** | `.harness/contracts/*` (this file, schemas) + `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` | How changes are proposed, reviewed, and merged |
| **Coordination** | HermesProof MCP (`hermes3d-locks` + `hp-mha-serena` stdio subprocesses, already wired in `Set-ClaudeDesktopGateway.ps1`) | Anonymous role claims (BUILDER/CRITIC/SCRIBE/GATE-SMITH/DOC-KEEPER/WATCHDOG, 30-min TTL), hash-chained evidence ledger, file locks, gate enforcement |

## Standing rules (every layer must honor these)

1. **Security first** — see `docs/threat-model.md` and `.claude/principles.md`.
2. **Stdlib-only by default** — Python code uses stdlib unless an explicit decision
   is recorded in `.claude/notes.md`.
3. **Fail closed, fail loudly** — missing keys, missing config, broken invariants
   surface as clear errors at startup, not silent 200s at request time.
4. **Test before claiming done** — `.claude/verifiers/run.sh` after every Edit.

## How to invoke a Skill

Skills live under `.harness/skills/<name>/SKILL.md`. The Claude Code / MCP host
auto-discovers them when the working directory contains a `.claude/` folder with
skill manifests, OR you can invoke by name:

```
/minimax-cost-report --since=24h
/proxy-cache-tune --window=7d
/watchdog-self-test
/minimax-failover-drill
/claude-permission-repair
/playwright-verify --url=http://127.0.0.1:48217/readyz
```

Each Skill's `SKILL.md` declares:
- **frontmatter** (YAML): name, description, when-to-use, prerequisites
- **inputs** (JSON Schema): arguments the Skill accepts
- **procedure**: numbered steps the agent should follow
- **outputs**: what the Skill returns (file paths, JSON shapes, exit codes)
- **hermes_trace**: which HermesProof MCP calls to make (see below)
- **examples**: real invocations with expected results

## HermesProof integration (every Skill records evidence)

Every Skill in this repo records its execution as a hash-chained evidence entry
via the HermesProof MCP server (`hermes3d-locks`). The integration is mandatory
— a Skill that runs without appending evidence is treated as failed by
`hermes_complete_work`'s `gates_required` policy.

**Standard trace pattern**:

```
1. hermes_anonymous_claim  role=BUILDER  ttl_minutes=10
   # Or pick the role that matches the skill's nature:
   #   BUILDER — writes code or files
   #   CRITIC  — only reads + reports
   #   SCRIBE  — produces a doc / report
   #   WATCHDOG — kills / restarts processes
   #   DOC-KEEPER — updates .claude/notes.md
   #   GATE-SMITH — runs a verifier or gate

2. hermes_lock_files  <files touched by this skill>
   # Optional but recommended if the skill edits any file.

3. <do the work>

4. hermes_append_evidence  kind=<skill_name>
                           summary=<one-line outcome>
                           data={"duration_s": <n>, "verifier": "<gate that passed>"}

5. hermes_record_outcome  merge   # or lgtm / timeout / reject

6. hermes_anonymous_release  role=BUILDER
```

The helper at `scripts/hermes-call.ps1` wraps steps 1, 4, 5, 6 in a single
PowerShell command so Skills can do `scripts/hermes-call.ps1 trace -skill <name>
-summary "<text>"` and get the canonical sequence.

## How to add a new Skill

1. Create `.harness/skills/<your-skill>/SKILL.md` with the structure above.
2. If it accepts inputs, add a JSON Schema to `.harness/contracts/`.
3. If it shells out, add a `scripts/<your-skill>.ps1` or `.py` co-located.
4. Add the HermesProof trace section listing which `hermes_*` tool calls it makes.
5. Add a test under `tests/test_<your-skill>.py` that runs the procedure
   against the offline proxy stub.
6. Reference the Skill from `CONTRIBUTING.md` under "Adding a Skill".

## How to add a new MCP connector

1. Document the connector under `.harness/connectors/<name>.md` with: URL,
   install command, required env vars, transport.
2. Add the entry to `Set-ClaudeDesktopGateway.ps1`'s `$managedMcpServers`.
3. Reference it from `CONTRIBUTING.md` under "Adding a connector".

## Contract precedence

When something is unclear, this is the order:

1. `SECURITY.md` (always)
2. `.claude/principles.md` (security + style)
3. `.claude/CLAUDE.md` (project charter)
4. `.harness/HARNESS.md` (this file)
5. `docs/architecture.md` (system design)
6. `docs/threat-model.md` (security design)
7. Skill-specific `SKILL.md` (procedure)
8. JSON Schema in `.harness/contracts/` (input validation)

When in doubt, ask. Don't guess on auth, security, or key handling.