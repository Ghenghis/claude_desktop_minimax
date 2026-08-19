---
name: daveai-android-e2e
description: Explore and verify Android app behavior with scrcpy-mcp/ADB, then turn successful critical paths into deterministic Maestro regression flows with screenshots and log evidence.
---

# Android E2E

1. Confirm designated package and test device/emulator; do not touch unrelated devices.
2. Record `adb devices`, package/version, orientation and starting app state; redact device serial in final reports.
3. Use scrcpy-mcp for fast visual/UI/device exploration; use ADB-only fallback if scrcpy is unavailable.
4. Do not use arbitrary `shell_exec` when a narrower Android tool can perform the task.
5. Once a path works, encode it as a Maestro flow rather than relying on repeated free-form taps.
6. Avoid fixed sleeps; use visible-state assertions/waits.
7. Capture failure evidence before repair.
8. Re-run from a clean app state/relaunch.
9. Save flow, result, screenshot(s), relevant log slice and artifact hash into `.agent/evidence/`.
