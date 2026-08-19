---
name: daveai-android-e2e
description: Author and run deterministic Android end-to-end flows with Maestro.
---

# daveai-android-e2e

**Use when:** a mobile UI flow needs repeatable proof or regression detection

## Steps
- Confirm the device/emulator is connected and authorized.
- Explore the flow once with scrcpy-mcp to identify IDs/text.
- Write the Maestro YAML flow.
- Run the flow with maestro test and capture the output.
- On failure, attach screenshot and log.

## Proof required
passing Maestro flow output or failure screenshot/log
