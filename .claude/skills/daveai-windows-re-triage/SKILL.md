---
name: daveai-windows-re-triage
description: Triage a Windows binary for static vs dynamic analysis.
---

# daveai-windows-re-triage

**Use when:** faced with an unknown Windows executable, DLL, or installer

## Steps
- Hash the file and record the target architecture and compiler hints.
- Run strings, resources, and PE overview.
- Decide: static-only, x64dbg Automate, or Hyper-V isolated lab.
- For dynamic: snapshot VM, set breakpoints, capture trace.
- For static: produce a triage report with imports, exports, and suspicious APIs.

## Proof required
RE_TRIAGE_REPORT.md with hashes, architecture, and chosen lane
