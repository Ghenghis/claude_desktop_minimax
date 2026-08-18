# Claude-Desktop MiniMax V2 — Registry Wiring

## 1. Registry path

```
HKCU:\SOFTWARE\Policies\Claude
```

All values are strings unless otherwise noted.

## 2. Visual wiring diagram

```mermaid
flowchart TB
    subgraph Reg["HKCU\\SOFTWARE\\Policies\\Claude"]
        P["inferenceProvider = gateway"]
        U["inferenceGatewayBaseUrl = http://127.0.0.1:48217/anthropic"]
        K["inferenceGatewayApiKey = proxy-managed"]
        S["inferenceGatewayAuthScheme = x-api-key"]
        D["modelDiscoveryEnabled = true"]
        M["inferenceModels = JSON"]
        MCP["managedMcpServers = JSON"]
        LDE["isLocalDevMcpEnabled = true"]
    end
    CD["Claude Desktop"]
    GW["gateway"]
    MM["minimax-media MCP"]
    H3["hermes3d-locks MCP"]

    Reg -->|1. chat model config| CD
    CD -->|2. HTTP| GW
    Reg -->|3. local MCP list| CD
    CD -->|4. stdio| MM
    CD -->|4. stdio| H3
```

## 3. inferenceModels JSON shape

```json
[
  {
    "name": "claude-sonnet-4-5",
    "labelOverride": "MiniMax M3",
    "anthropicFamilyTier": "sonnet",
    "supports1m": true,
    "isFamilyDefault": true
  },
  {
    "name": "claude-opus-4-6",
    "labelOverride": "MiniMax M2.7",
    "anthropicFamilyTier": "opus",
    "isFamilyDefault": true
  },
  {
    "name": "claude-haiku-4-5",
    "labelOverride": "MiniMax M2.7 Highspeed",
    "anthropicFamilyTier": "haiku",
    "isFamilyDefault": true
  },
  {
    "name": "claude-sonnet-4",
    "labelOverride": "MiniMax M3 (legacy)",
    "anthropicFamilyTier": "sonnet",
    "supports1m": true
  },
  {
    "name": "claude-opus-4",
    "labelOverride": "MiniMax M2.7 (legacy)",
    "anthropicFamilyTier": "opus"
  },
  {
    "name": "claude-haiku-4",
    "labelOverride": "MiniMax M2.7 Highspeed (legacy)",
    "anthropicFamilyTier": "haiku"
  }
]
```

## 4. managedMcpServers JSON shape

```json
[
  {
    "name": "minimax-media",
    "transport": "stdio",
    "command": "C:\\Python314\\python.exe",
    "args": [
      "G:\\Github\\Testing-Claude-Minimax-Mcp\\minimax-mcp-server\\server.py"
    ],
    "toolPolicy": { "*": "allow" }
  }
]
```

The `command` is discovered at setup time by `Set-ClaudeDesktopGateway.ps1` so it always points at a Python interpreter that has the `mcp` package installed.
