---
name: daveai-apk-re-triage
description: Triage an authorized Android APK/AAB without destructive changes, choose the minimum reverse-engineering toolchain, and produce a reproducible evidence-backed report. Use before editing or dynamically instrumenting an Android app.
---

# APK Reverse-Engineering Triage

1. Preserve original and SHA-256; analyze a working copy.
2. Record package name, version, min/target SDK, signing info, ABIs, manifest components, permissions and native libraries.
3. Detect ordinary Java/Kotlin versus framework/engine indicators, especially Unity Mono/IL2CPP.
4. Route:
   - Java/Kotlin -> JADX;
   - resources/smali -> Apktool;
   - native `.so` -> one native analyzer;
   - unresolved runtime question -> Frida profile;
   - Unity -> unity router.
5. Static analysis comes before dynamic analysis unless the task is explicitly runtime-only.
6. Every conclusion cites an evidence location: class/method/xref/resource/native symbol/runtime observation.
7. Never overwrite the original package.
