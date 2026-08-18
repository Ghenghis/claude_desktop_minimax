# Claude-Desktop MiniMax V2 — End-to-End Data Flow

## 1. Full E2E sequence

```mermaid
sequenceDiagram
    actor U as User
    participant CD as Claude Desktop
    participant Reg as Windows Registry
    participant GW as Gateway
    participant PU as port_util
    participant Key as G:\private\minimax_key.txt
    participant MM as MiniMax

    U->>PU: Start-ClaudeMinimaxV2.ps1
    PU->>PU: find_free_port(48217)
    PU->>PU: write .port
    PU->>GW: start python -m gateway.server
    PU->>Reg: Set-ClaudeDesktopGateway.ps1
    Reg->>CD: inferenceGatewayBaseUrl, inferenceModels, managedMcpServers
    U->>CD: restart Claude Desktop
    CD->>Reg: load 3P settings
    CD->>GW: GET /v1/models
    GW->>MM: list MiniMax models
    MM-->>GW: models
    GW-->>CD: Anthropic-shaped list with labelOverride
    CD->>CD: render "MiniMax M3" picker
    U->>CD: send message
    CD->>GW: POST /v1/messages (claude-sonnet-4-5)
    GW->>Key: load key
    GW->>GW: resolve to MiniMax-M3
    GW->>MM: POST MiniMax /v1/messages
    MM-->>GW: streaming completion
    GW-->>CD: Anthropic streaming completion
    CD-->>U: answer
```

## 2. Registry key map

| Registry value | Purpose |
|---|---|
| `inferenceProvider` | `gateway` |
| `inferenceGatewayBaseUrl` | `http://127.0.0.1:<port>/anthropic` |
| `inferenceGatewayApiKey` | `proxy-managed` (ignored by proxy) |
| `inferenceGatewayAuthScheme` | `x-api-key` |
| `modelDiscoveryEnabled` | `true` |
| `inferenceModels` | JSON array of 6 Claude-family IDs with `labelOverride` |
| `managedMcpServers` | JSON array of stdio MCPs (minimax-media, hermes3d-locks, etc.) |
| `isLocalDevMcpEnabled` | `true` |

## 3. Model picker rewrite

```mermaid
flowchart LR
    CD["Claude Desktop model picker"]
    Reg["Registry inferenceModels"]
    GW["gateway /v1/models"]
    MM["MiniMax"]
    CD -->|displays| Reg
    Reg -->|labelOverride| CD
    CD -->|uses internal ID "claude-sonnet-4-5"| GW
    GW -->|resolve_model| MM
```
