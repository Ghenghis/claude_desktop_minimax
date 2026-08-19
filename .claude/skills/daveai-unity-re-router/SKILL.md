---
name: daveai-unity-re-router
description: Route Unity game/binary analysis to the correct tool for the engine version.
---

# daveai-unity-re-router

**Use when:** target is a Unity build using IL2CPP or Mono

## Steps
- Identify engine version and scripting backend (IL2CPP vs Mono).
- For assets: use AssetRipper.
- For IL2CPP: use Cpp2IL.
- For managed assemblies: use dnSpyEx.
- For native code: use r2unity/radare2.
- Record the tool choice and findings in RE_TRIAGE_REPORT.md.

## Proof required
RE_TRIAGE_REPORT.md with Unity version, backend, and routed tools
