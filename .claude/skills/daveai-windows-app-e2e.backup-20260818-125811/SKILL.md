---
name: daveai-windows-app-e2e
description: Build, launch and verify Windows desktop applications for a non-coder user using native Windows tooling and deterministic UI evidence. Use for WinUI, Win32, WPF, Electron/Rust/.NET Windows app work.
---

# Windows App E2E

1. Detect framework and existing build/test commands before adding tooling.
2. Use WinApp CLI/win-dev-skills for Windows-native setup/package/UI Automation where appropriate.
3. Use project-native unit/integration tests first.
4. Use WinApp UI automation or Playwright for the actual GUI layer depending on app technology.
5. Capture the exact failure before fixing it.
6. After repair, rebuild, relaunch, reproduce the user flow and verify visible state.
7. Record artifact hash and test evidence.
8. Do not declare success from compilation alone.
