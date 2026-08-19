# Claude-Desktop MiniMax V2 — System Architecture

## 1. High-level block diagram

```mermaid
flowchart TB
    subgraph User["Windows 11 User"]
        CD["Claude Desktop"]
    end

    subgraph Windows["Windows 11 OS"]
        Reg[(HKCU\\SOFTWARE\\Policies\\Claude)]
        Key["G:\\private\\minimax_key.txt"]
    end

    subgraph Gateway["claude-minimax-v2 (Python)"]
        SRV["HTTP gateway\n127.0.0.1:48217"]
        PA["anthropic_passthrough"]
        AL["model_aliases"]
        MU["modality proxy"]
    end

    subgraph API["MiniMax APIs"]
        MA["Anthropic-compatible\n/v1/messages"]
        MM["Media APIs\nT2A, image, video, music"]
    end

    CD <-->|HTTP /v1/messages, /v1/models| SRV
    SRV --> PA
    PA --> AL
    PA -->|rewrite model + stream| MA
    SRV --> MU
    MU -->|/t2a_v2, /image_generation, /video_generation, /music_generation| MM
    Reg -->|inferenceGatewayBaseUrl, inferenceModels| CD
    Key -->|read at request time| SRV
    Key -->|read at tool call time| MM
```

## 2. Component responsibilities

- **Claude Desktop**: Anthropic client that reads 3P gateway config from the Windows registry.
- **HKCU registry**: tells Claude where the gateway is and which model names to display.
- **claude-minimax-v2/gateway/server.py**: thin HTTP server that exposes `/anthropic/v1/messages` and `/v1/models` and a `/ui` playground.
- **anthropic_passthrough.py**: transparent proxy from Anthropic schema to MiniMax's Anthropic-compatible endpoint; rewrites model names.
- **model_aliases.py**: maps `claude-sonnet-*`, `claude-opus-*`, `claude-haiku-*` to `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`.
- **port_util.py**: binds to the preferred port `48217` or an ephemeral fallback; writes `.port` for the registry script.
- **Start-ClaudeMinimaxV2.ps1**: stops stale gateway, finds free port, starts `server.py`, writes `.port`, calls `Set-ClaudeDesktopGateway.ps1`.
- **Set-ClaudeDesktopGateway.ps1**: writes all HKCU values and the `managedMcpServers` list.
- **Repair-ClaudeMinimaxV2.ps1**: idempotent hard reset (stop, py_compile, clear `.port`, restart).

## 3. Data flow for one chat message

```mermaid
sequenceDiagram
    actor U as User
    participant CD as Claude Desktop
    participant GW as Gateway
    participant MM as MiniMax API
    U->>CD: pick "MiniMax M3"
    CD->>GW: POST /anthropic/v1/messages<br/>{model:"claude-sonnet-4-5", messages:[...]}
    GW->>GW: resolve_model("claude-sonnet-4-5") => "MiniMax-M3"
    GW->>GW: load_minimax_key() from G:\private\minimax_key.txt
    GW->>MM: POST https://api.minimax.io/v1/...<br/>{model:"MiniMax-M3", ...}
    MM-->>GW: SSE / JSON streaming chunks
    GW-->>CD: Anthropic-shaped SSE chunks
    CD-->>U: displayed response
```

## 4. Port and file layout

```mermaid
flowchart LR
    subgraph Ports["Network"]
        P1["127.0.0.1:48217<br/>gateway"]
        P2["Claude Desktop\nmain process"]
    end
    subgraph Files["Private + GitHub"]
        F1["G:\\private\\minimax_key.txt"]
        F2["G:\\private\\.proxy-token"]
        F3["G:\\Github\\claude-minimax-v2"]
        F4["G:\\Github\\claude-codex-devin"]
    end
    P2 -->|HTTP 127.0.0.1:48217| P1
    P1 -->|reads| F1
    P2 -->|reads registry| Reg
    F4 -->|Start / Repair / Set scripts| P2
```
