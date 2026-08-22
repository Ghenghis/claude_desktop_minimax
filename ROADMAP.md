# MiniMax Desktop Integration — Action Plan & Roadmap

Goal: Claude Desktop and Codex Desktop fully driven by MiniMax — text, image,
speech, video, voices — stable, self-healing, and verifiable. Progress is
tracked per pass; every item has an acceptance criterion and an evidence
command. Run `.\Test-MiniMaxStack.ps1` (the interactive harness) at any time
to check the whole stack.

Legend: `[x]` done+verified · `[~]` in progress · `[ ]` pending

---

## Layered Audit (current state)

| Layer | Claude Desktop | Codex Desktop |
|---|---|---|
| L1 Text gateway | `claude-minimax-proxy` service :48217 — OK | `api2codex` service :48218 — OK |
| L2 Model picker | 8 slots visible, tier-mapping fixed (M3 / M2.7 / Highspeed) | `model_catalog_json` wired; CLI catalog resolves 3 MiniMax models; Desktop picker render pending restart (known upstream filter issues #19694/#37379) |
| L3 MCP orchestration | `mini` single server — OK (daves-tools 6 tools) | `mini` single server — OK |
| L4 Media/tools | Official `minimax` 8 tools + custom media 4 + coding-plan vision/search, all via mini | same via mini (shared) |
| L5 Reliability harness | services + disabled watchdog; no smoke-test | services; no smoke-test |
| L6 Docs/evidence | AGENTS.md runbook | AGENTS.md runbook |

## Open-source cross-references (patterns adopted)

- **MiniMax-AI/MiniMax-MCP (official)** — installed in an isolated venv and
  verified: `text_to_audio`, `list_voices`, `voice_clone`, `voice_design`,
  `play_audio`, `text_to_image`, `generate_video`, `query_video_generation`.
- **MiniMax coding-plan MCP** — installed in a pinned venv and verified:
  `web_search`, `understand_image`.
- **megamen32 gist / Keksuccino Better-Codex-App-Custom-Provider-Support** —
  `model_catalog_json` schema for MiniMax models in the Codex picker; also the
  documented Desktop filtering workaround (block `ab.chatgpt.com`, clear WebView
  Local Storage) if the picker hides catalog models.
- **alnsergeev/codex-profile-launcher** — profile-file pattern
  (`~/.codex/<name>.config.toml`) for switching OpenAI ↔ MiniMax backends.
- **LiteLLM proxy** — evaluated; hangs on this host (see AGENTS.md). Custom
  proxy remains primary; keep LiteLLM disabled unless upstream fixes land.
- **MiniMax platform notes** — Music Generation API is discontinued for new
  users as of 2026-08-20 (existing paying users unaffected); speech-2.8-hd is
  current TTS flagship; Hailuo-2.3 / MiniMax-H3 are current video models;
  video flow is async: create → poll → file retrieve.

---

## Pass 1 — Stabilize text core (DONE)

- [x] Claude gateway on C:, Windows service, token auth, sanitizer
      — Evidence: `sc query claude-minimax-proxy`; POST :48217 returns clean text
- [x] Codex gateway (`api2codex`) on C:, Windows service
      — Evidence: `sc query api2codex`; POST :48218/v1/responses returns text
- [x] `max_output_tokens` mapping; thinking/reasoning stripping in both proxies
- [x] `mini` MCP orchestrator with daves-tools fixed (6 tools)
- [x] LiteLLM evaluated, documented, disabled (startup hang)

## Pass 2 — Truthful model pickers (IN PROGRESS)

- [x] Claude: MODEL_MAP tiers fixed — sonnet→M3, opus→M2.7, haiku→M2.7-highspeed
      — Evidence: 3 aliases POSTed, upstream model echoed per tier
- [x] Codex: `model_catalog_json` built from bundled catalog + 3 MiniMax models
      — Evidence: `codex debug models` lists MiniMax-M3/M2.7/M2.7-highspeed
- [ ] Codex Desktop restart → confirm picker shows MiniMax entries
      — If hidden: apply documented workaround (hosts entry for `ab.chatgpt.com`,
        delete WebView `Local Storage\leveldb`, full restart)
- [ ] Claude: verify picker slot labels match actual routed models in a live chat
      (ask "which model are you?" per slot is unreliable; use proxy log evidence)
- [ ] Optional: 1M-context slots (`supports1m`) verified against MiniMax M3 1M

## Pass 3 — Complete media tooling (image, speech, voices, video)

Target: parity with official MiniMax-MCP tool set, served through `mini` so
both chat UIs get the same tools.

- [~] `minimax-media` server pinned to C: + registered in mini with env
- [x] Official MCP provides `list_voices`, `voice_clone`, `voice_design`, and
      `query_video_generation`; verified through `mini ls minimax`
- [x] Add custom Files list/retrieve/download and Video Agent create/query tools
      to `minimax-media`; verified through `mini ls minimax-media`
- [ ] Add `minimax_voice_clone` custom fallback (official tool already covers it)
- [ ] Extend `minimax_generate_video`: image-to-video (`first_frame_image`),
      Hailuo-2.3 / Hailuo-2.3-Fast models, 768P/1080P validation
- [ ] Image tool: add `width`/`height` custom dims (image-01 update),
      `subject_reference` support
- [ ] Music tool: keep but mark deprecated for new users (platform change
      2026-08-20); fail with clear message if account lacks access
- [ ] Smoke test each tool once (minimal cost): speech 1 short line, image 1
      small, voices list (free), video only on explicit approval (expensive)
- [ ] Verify all tools visible in BOTH Claude Desktop and Codex chat UIs via mini

## Pass 4 — Harness: never silently break

- [ ] `Test-MiniMaxStack.ps1` interactive harness (this repo):
      checks services, ports, both gateways per-model, registry, catalog,
      mini status, minimax-media handshake; `-Fix` restarts what's down
- [ ] Wire harness as scheduled task (daily + on logon, silent, log to file)
- [ ] Service recovery settings: restart on failure for both gateway services
      (WinSW `onfailure` already set; verify with forced kill test)
- [ ] `mini` startup resilience: startup_timeout_sec tuned; stale G:-path
      registrations removed (minimax-media done; audit serena/unity entries)
- [ ] Single source of truth for secrets: `C:\private\.env` +
      `C:\private\.proxy-token` only; no G:/S: fallbacks in hot paths
- [ ] Kill-test evidence: force-kill each gateway process → service auto-restarts
      → endpoint answers within 30s

## Pass 5 — Polish, docs, proof ledger

- [ ] AGENTS.md updated with media tools, harness usage, catalog notes
- [ ] Proof ledger table: every Pass 2–4 item with command + timestamp + result
- [ ] Backup sync: mirror final scripts/configs to G:\Github\claude-codex-devin
- [ ] Optional niceties: Codex profile files (`minimax.config.toml` as
      `--profile minimax`), Claude picker label cleanup, output folder
      `C:\Users\Admin\MiniMax-Generated` shortcut

---

## What is intentionally out of scope

- Claude Desktop native image rendering of generated files (client limitation;
  tools return local file paths)
- Codex Desktop picker fixes that require patching the Electron bundle
  (tracked upstream; workaround documented instead)
- Music generation for new accounts (MiniMax discontinued the API 2026-08-20)

## Standing verification commands

```powershell
# Full stack check
powershell -ExecutionPolicy Bypass -File C:\Users\Admin\claude-codex-devin\Test-MiniMaxStack.ps1

# Claude gateway per-tier
#   claude-sonnet-4-5 -> MiniMax-M3, claude-opus-4-6 -> MiniMax-M2.7,
#   claude-haiku-4-5 -> MiniMax-M2.7-highspeed
# Codex effective model catalog
& 'C:\Users\Admin\AppData\Local\OpenAI\Codex\bin\110b3d66a02d864e\codex.exe' debug models
# MCP status
& 'C:\Users\Admin\go\bin\mini.exe' status
```
