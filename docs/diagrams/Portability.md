# Claude-Desktop MiniMax V2 — Portability Plan

## 1. Portable bundle layout

```mermaid
flowchart LR
    subgraph Zip["claude-minimax-v2-portable.zip"]
        root["start-here.bat"]
        read["README-PORTABLE.txt"]
        CM["claude-codex-devin/"]
        MMV["claude-minimax-v2/"]
    end
    PC["Clean Windows 11 PC"]
    PRIV["C:\\private\\minimax_key.txt"]
    CD2["Claude Desktop"]

    Zip -->|extract| PC
    PRIV --> PC
    PC -->|run start-here.bat| PC
    PC -->|install.ps1 checks| PC
    PC -->|Start-ClaudeMinimaxV2.ps1| CM
    CM -->|starts| MMV
    CD2 -->|restart| PC
```

## 2. start-here.bat flow

```mermaid
flowchart TB
    A[Double-click start-here.bat] --> B{Python installed?}
    B -->|No| C[Show error and pause]
    B -->|Yes| D[py_compile all .py]
    D -->|Fail| C
    D -->|Pass| E{MiniMax key in C/G/S:\private?}
    E -->|No| F[Create C:\private and pause]
    E -->|Yes| G[Start-ClaudeMinimaxV2.ps1]
    G --> H[Write .port]
    H --> I[Set-ClaudeDesktopGateway.ps1]
    I --> J[Restart Claude Desktop]
```

## 3. Build script

- `claude-codex-devin\portable\Build-PortableZip.ps1`:
  1. Copies `claude-codex-devin` and `claude-minimax-v2` to temp.
  2. Excludes `.git`, `.venv`, `__pycache__`, `.hermes3d_orchestrator`.
  3. Generates top-level `start-here.bat` and `README-PORTABLE.txt`.
  4. Compresses to `G:\Github\claude-minimax-v2-portable.zip`.

## 4. Requirements on the target PC

- Windows 11
- Python 3.11+ on `PATH`
- MiniMax API key in `C:\private\minimax_key.txt` (or `G:\` / `S:\`)
- Claude Desktop installed
- No other claude-minimax-v2 gateway on the same port
