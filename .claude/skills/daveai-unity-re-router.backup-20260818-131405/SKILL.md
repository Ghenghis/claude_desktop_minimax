---
name: daveai-unity-re-router
description: Detect a Unity application's managed/native layout and route authorized analysis to the correct minimal toolchain. Use when APK/Windows game analysis identifies Unity files, assemblies or IL2CPP metadata.
---

# Unity RE Router

Detect first; do not launch every Unity tool.

- Assets/resources -> AssetRipper.
- Mono managed assemblies -> dnSpyEx/managed decompiler.
- IL2CPP -> Cpp2IL; use r2unity/native analyzer for metadata/native correlation when needed.
- Native engine/plugin libraries -> radare2 or Ghidra.

Record Unity version clues, architecture, metadata files and selected route in the triage report.
