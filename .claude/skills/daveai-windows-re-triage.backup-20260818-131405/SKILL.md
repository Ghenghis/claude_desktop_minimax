---
name: daveai-windows-re-triage
description: Triage an authorized Windows binary, choose static versus dynamic tooling, isolate risky work, and produce evidence-backed reverse-engineering findings. Use before x64dbg/WinDbg or binary modifications.
---

# Windows RE Triage

1. Preserve original and SHA-256.
2. Identify PE architecture, managed/native status, imports/exports, sections, signatures and framework/runtime clues.
3. Route managed code to managed tooling; route native static work to one analyzer.
4. Use x64dbg Automate MCP only when runtime state is needed.
5. Use WinDbg only for a WinDbg-specific need such as dumps/kernel/driver cases.
6. Use Hyper-V isolation for unknown/risky binaries, driver/kernel work or fragile system changes.
7. Restrict dynamic attachment to the designated target process.
8. Record reproducible evidence for each conclusion.
