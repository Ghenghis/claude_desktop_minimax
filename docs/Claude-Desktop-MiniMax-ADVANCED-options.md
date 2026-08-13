# Claude Desktop + MiniMax — Advanced / Upgrade Options

**This is a planning document, not yet applied.** The baseline in `Claude-Desktop-MiniMax-BASELINE-VERIFIED.md` is confirmed working and must not be modified until any option below is tested and separately verified.

Answers below are fact-checked against MiniMax's official docs (`platform.minimax.io/docs/api-reference/text-anthropic-api`, `.../guides/models-intro`, `.../release-notes/models`) as of 2026-08-10.

## 1. Can we select MiniMax's other text models (M2.7, M2.5, M2.1, M2) instead of just M3?

**Yes, technically possible — MiniMax's Anthropic-compatible endpoint (`/anthropic/v1/messages`) officially supports these `model` values:**

| MiniMax model | Context window | Notes |
|---|---|---|
| `MiniMax-M3` | 1,000,000 | Flagship, multimodal (text+image+video), agentic/coding |
| `MiniMax-M2.7` | 204,800 | text + tool calls only, no image/video |
| `MiniMax-M2.7-highspeed` | 204,800 | same as M2.7, ~100 tps |
| `MiniMax-M2.5` | 204,800 | text + tool calls only |
| `MiniMax-M2.5-highspeed` | 204,800 | same as M2.5, faster |
| `MiniMax-M2.1` | 204,800 | text + tool calls only |
| `MiniMax-M2.1-highspeed` | 204,800 | same as M2.1, faster |
| `MiniMax-M2` | 204,800 | text + tool calls only |

There is no `MiniMax-2.5`/`2.1` as standalone names, and no `MiniMax-M1` in the current Anthropic-compatible catalog — the closest matches to what you described are `M2.7`, `M2.5`, and `M2.1`.

**How you could expose more than one in Claude Desktop's picker:** Claude Desktop's model picker groups models by an Anthropic "family tier" (`sonnet`, `opus`, `haiku`). The current `inferenceModels` registry entry only defines one (`claude-sonnet-4-5` → `sonnet` tier). You could add two more entries, e.g.:

```json
[
  {"name":"claude-sonnet-4-5","anthropicFamilyTier":"sonnet","supports1m":true},
  {"name":"claude-opus-4-6","anthropicFamilyTier":"opus"},
  {"name":"claude-haiku-4-5","anthropicFamilyTier":"haiku"}
]
```

...and update the proxy's `MODEL_MAP` to route each Anthropic name to a different MiniMax model, e.g. `claude-sonnet-4-5 -> MiniMax-M3`, `claude-opus-4-6 -> MiniMax-M2.7`, `claude-haiku-4-5 -> MiniMax-M2.1`. This would give three selectable "models" in the picker, each secretly a different MiniMax model. **Not yet implemented or tested** — would need its own verification pass (repeat the same automated test pattern against each mapped model).

Caveat: only `MiniMax-M3` supports image/video input; the picker labels would be misleading unless documented for the user (e.g. picking "Haiku" might silently drop image attachments since M2.1 rejects image blocks).

## 2. Can we use MiniMax's vision (image understanding) model through Claude Desktop chat?

**Yes — this already works with zero proxy changes**, because:

- The proxy forwards message bodies untouched except for the `model` field.
- MiniMax-M3 (which every current request is routed to) natively supports `type: "image"` content blocks in the Anthropic Messages format (JPEG/PNG/GIF/WEBP, up to 10 MB, base64 or URL).
- If Claude Desktop's UI lets you attach an image to a chat message, it will format it as an Anthropic image content block and it will reach M3 exactly as designed.

**Not yet manually verified in this session.** To verify: attach an image in Claude Desktop chat and ask a question about it; confirm the response references the image content correctly. If it fails, check the proxy log window for the raw request/response.

Only `MiniMax-M3` supports image input — `M2.x` models do not, per MiniMax's docs. If you add multi-model picker slots (option 1) mapped to `M2.x`, vision would silently break on those slots.

## 3. Can we use MiniMax's video input (M3 supports video understanding) in chat?

Same mechanism as vision — M3 accepts `type: "video"` content blocks (MP4/AVI/MOV/MKV, up to 50 MB inline or 512 MB via MiniMax's Files API with an `mm_file://{file_id}` reference). Whether this works depends entirely on whether Claude Desktop's UI supports attaching video files to a chat message — most chat clients (including Claude Desktop) are built around Anthropic's supported attachment types, which historically has been images and documents, not raw video. **Untested and likely unsupported by the Claude Desktop UI itself**, independent of MiniMax's capability.

## 4. Can we use MiniMax's voice/text-to-speech (T2A) models in Claude Desktop chat?

**No — not through chat, and this is a hard limitation of Claude Desktop's architecture, not something a proxy can fix.**

- MiniMax's T2A (text-to-speech) API is a completely separate REST endpoint family (`speech-2.8-hd`, `speech-2.8-turbo`, `speech-02-hd`, etc.), unrelated to the Anthropic Messages API (`/anthropic/v1/messages`) that Claude Desktop's gateway calls.
- Claude Desktop's third-party gateway mode only ever calls the Messages API — it has no concept of, or hook for, calling a separate audio-synthesis endpoint mid-conversation.
- The only path to make this usable inside Claude Desktop would be building a **local MCP (Model Context Protocol) server** that wraps MiniMax's T2A API as a callable "tool," and having Claude call that tool (e.g. "generate audio of this text") — the assistant's text response would then include a link/file to the generated audio, not live in-chat voice playback. This is a separate integration project, not a config change.

## 5. Can we use MiniMax's image generation (`image-01`) or video generation (Hailuo / MiniMax H3) models in Claude Desktop chat?

**No, not natively — same reasoning as voice.** Image/video *generation* APIs are separate REST endpoints (`POST /v1/image_generation`, `POST /v1/video_generation`, etc.), not part of the Anthropic Messages API. Claude Desktop's gateway mode cannot call them directly.

The only way to expose this inside a Claude Desktop conversation is the same MCP-tool-server approach as voice: a local MCP server that exposes "generate an image" / "generate a video" as tools, which Claude (running on M3, which supports tool calls) could invoke. The result would come back as a tool result (e.g. a file path or URL) that Claude then shows you — this is not the same as a native in-chat "media generation" experience, but it is achievable with additional engineering.

## Summary table

| Feature | Works today (baseline) | Possible with more work | Not possible via Claude Desktop chat |
|---|---|---|---|
| Text chat via MiniMax-M3 | ✅ | | |
| Selecting M2.7 / M2.5 / M2.1 / M2 in the picker | ❌ | ✅ (multi-slot proxy mapping) | |
| Vision (image understanding, M3 only) | ✅ (untested manually, should work) | | |
| Video understanding (M3 only) | ❌ (untested, UI-dependent) | ✅ if Claude Desktop UI allows video attachments | |
| Text-to-speech (voice output) | ❌ | ✅ only via a custom MCP tool server | Native in-chat voice — no |
| Image generation | ❌ | ✅ only via a custom MCP tool server | Native in-chat generation — no |
| Video generation | ❌ | ✅ only via a custom MCP tool server | Native in-chat generation — no |

## Recommendation

- Keep the verified baseline exactly as-is (`Claude-Desktop-MiniMax-BASELINE-VERIFIED.md`).
- If you want the multi-model picker (option 1) or to confirm vision works (option 2), those are low-risk, additive changes — happy to implement and test them next, in a way that doesn't disturb the current working config (e.g. test in a branch of the proxy/registry script first).
- Voice and generation features (options 4 and 5) require a genuinely new component (an MCP tool server) — bigger scope, should be its own project if you want it.
