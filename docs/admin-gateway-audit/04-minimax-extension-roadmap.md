# Admin Gateway × MiniMax — Modality Extension Roadmap (Aug 2026)

**Scope:** What the local Admin Gateway (`G:\Github\claude-codex-devin\claude-minimax-proxy.py`) can become once it fronts every MiniMax modality, not only text. The Claude Desktop picker currently shows four Anthropic-looking slots (`claude-sonnet-4-5`, `claude-sonnet-4-5 1M`, `claude-opus-4-6`, `claude-haiku-4-5`) — three of them are mapped by `MODEL_MAP` to MiniMax text models. Adding the remaining MiniMax modalities means extending the proxy with new endpoints and exposing new picker slots.

## 1. Current state vs. full MiniMax surface

| Surface | Today (proxy) | MiniMax offers | Gap |
|---|---|---|---|
| Text chat (Anthropic-compat) | ✅ `/anthropic/v1/messages` | MiniMax-M3 / M2.7 / M2.7-highspeed / M2.5 / M2.1 / M2 / M2-her | Vision input only on M3; other text models reject multimodal parts |
| Text chat (OpenAI-compat) | ❌ | Same family via `/v1/chat/completions` | Cursor / Continue / Open WebUI / Aider could use MiniMax with zero SDK change |
| Image generation | ❌ | `image-01` (T2I, 512–2048 px, 8 aspect presets, sync base64) | High leverage |
| Video generation | ❌ | `MiniMax-H3` (T2V/I2V/multimodal) + legacy Hailuo 2.3 / 02 (1080p/768p, 6–10s) — async poll | Async pattern not yet in proxy |
| Speech / TTS | ❌ | `speech-2.8-hd` / `speech-2.8-turbo` + legacy 2.6 / 02 — 40 langs / 7 emotions | High call frequency; stateless sync endpoint |
| Long-form async TTS | ❌ | `/v1/t2a_async_v2` — ≤1M chars | Needed for audiobook / narration use cases |
| Voice clone | ❌ | `upload_clone_audio` → `upload_prompt` → `clone` — multipart | Multipart upload not in proxy today |
| Voice design | ❌ | `/v1/voice/design` — synthetic voice from text prompt | Tier-gated (Plus/Max exclude, Ultra + paygo include) |
| Music generation | ❌ | `music-3.0` (and `music-2.6`, `music-2.0`, `music-cover`) — async poll | Async + lyrics input |
| Lyrics generation | ❌ | `/v1/lyrics_generation` (sync) | Often paired with music |
| File management | ❌ | upload / list / retrieve / delete (multipart, Bearer) | Needed for video I2V and voice clone |
| Vision input for M3 | ✅ passes through | Image + video URL content parts | Already works; verify on M3-only routes |

## 2. Recommended picker-slot mapping (text + extension)

| Slot (Claude Desktop `inferenceModels`) | Maps to | Tier gated? |
|---|---|---|
| `claude-opus-4-6` (best) | `MiniMax-M3` — 1M ctx, vision+video input, coding | Token Plan (any) |
| `claude-sonnet-4-5` (balanced) | `MiniMax-M2.7` | Token Plan |
| `claude-haiku-4-5` (fast) | `MiniMax-M2.7-highspeed` ~100 tps | Token Plan |
| `claude-sonnet-4-5-1m` (1M context) | `MiniMax-M3` — 1M ctx | Token Plan |
| `claude-chat` (new slot, dialog) | `M2-her` 64k ctx | Token Plan |
| `claude-image-1` (new slot, T2I) | `image-01` | Token Plan + paygo; Free 10 RPM |
| `claude-video-1` (new slot, T2V) | `MiniMax-H3` → fallback `Hailuo 2.3` | Video Standard $1k+/mo |
| `claude-speech-1` (new slot, TTS) | `speech-2.8-hd` (turbo for low-latency) | Audio Starter+ |
| `claude-voice-clone-1` (new slot) | voice-clone pipeline | Audio Business or paygo |
| `claude-music-1` (new slot) | `music-3.0` | Audio Starter+ (120 RPM) |

The first four slots already work. The remaining six slots are the "what can we edit" answer — each new slot maps to one new proxy endpoint.

## 3. Per-extension required changes (proxy + registry)

Each row is a self-contained chunk of work that can ship independently.

### 3.1 OpenAI-compat chat — `POST /v1/chat/completions`
- **Path/header**: strip `/anthropic` prefix; rewrite `X-Api-Key` → `Authorization: Bearer <key>`; leave body untouched.
- **Proxy change**: ~30 min. Re-uses existing SSE chunked pass-through at `claude-minimax-proxy.py:229-240`.
- **Registry change**: none (Claude Desktop does not speak OpenAI; this is for Cursor / Aider / custom clients).

### 3.2 Image generation — `POST /v1/image_generation`
- **Path/header**: rewrite to `https://api.minimax.io/v1/image_generation`; Bearer swap; JSON pass-through; return base64 JSON (or proxy bytes with `Content-Disposition`).
- **Proxy change**: ~30 min.
- **Registry change**: add `claude-image-1` slot in `Set-ClaudeDesktopGateway.ps1:23` `inferenceModels` JSON.

### 3.3 Video generation — `POST /v1/video_generation` + `GET /v1/query/video_generation`
- **Async pattern**: create returns `task_id` immediately; client polls. The MCP server already implements this loop (`minimax-mcp-server/server.py` `_video_async_poll`).
- **Proxy change**: ~1 day. Mirror the MCP pattern: forward create → return task_id JSON → expose `GET /v1/video/{task_id}` that proxies `query_video_generation` → on completion, optionally download bytes and stream to client.
- **Registry change**: add `claude-video-1` slot. Note: video tier ($1k+/mo) is separate from Token Plan — usage charged against the Video Standard/Business plan, not against M3 chat quota.

### 3.4 Speech / TTS — `POST /v1/t2a_v2`
- **Path/header**: rewrite to `https://api.minimax.io/v1/t2a_v2`; Bearer swap; JSON body with text + `voice_setting`. Response is hex-encoded audio by default; the proxy can either return raw JSON (let client decode) or decode and stream `audio/mpeg` bytes with `Content-Disposition`.
- **Proxy change**: ~1 hour.
- **Registry change**: add `claude-speech-1` slot. (Note: TTS does NOT use the `inferenceModels` picker — it would be exposed as a separate MCP tool, since Claude Desktop picker only handles chat completions. The Admin Gateway itself does the picking, not the client picker.)

### 3.5 File upload — `POST /v1/files/upload`
- **Foundation** for image-to-video and voice clone.
- **Proxy change**: ~45 min. Add multipart pass-through (do NOT parse the body — stream bytes through, rewrite auth header).
- **No registry change**.

### 3.6 Voice clone pipeline — three calls + persistent voice-id storage
- `upload_clone_audio` → returns `voice_id`; `clone` → returns `voice_id`; store in `G:\private\voice_ids.json` (ACL'd like `.env`).
- **Proxy change**: ~1 day.
- **No registry change** (CLI tool, not picker).

### 3.7 Music generation — `POST /v1/music_generation` + async poll
- Same async pattern as video.
- **Proxy change**: ~1 day.
- **No registry change**.

## 4. Token Plan context (from agent 3 audit)

| Tier | Price | Quota | RPM / TPM | Notable | Recommended for Admin Gateway? |
|---|---|---|---|---|---|
| Plus | $20/mo | 5-hour rolling + weekly | Not published | Full MiniMax lineup; no H3 / voice design / rapid voice clone | No — same model catalog as Max |
| Max | $50/mo | 5-hour rolling + weekly | Not published | Same as Plus | No — same model catalog as Plus |
| **Ultra** | **$120/mo** | 5-hour rolling + weekly | **5,000 / 8,000,000** | `service_tier=priority` on M3 (1.5× admission); 6–7 concurrent agents | **Yes** — only tier with published RPM/TPM and priority admission |
| Pay-as-you-go | per-token | None | None | All models incl. H3 / voice design / rapid voice clone; MCP API-vlm $0.01/req | Yes for image/video/audio overage |

**Ultra + heavy single-user gateway cost estimate** (M3 default, 20 req/hr, 15k input + 5k output, 8h/day):
- Per hour: $0.21. Per day: ~$1.68. Per month variable: ~$55.
- Plus $120 Ultra seat = **~$175/month total**.

If video is desired, add a Video Standard ($1k/mo) seat on top — video usage is metered against the video plan, not against chat tokens. Most single users will not need that; skip video unless explicitly required.

## 5. Sources

- [models-intro (legacy section)](https://platform.minimax.io/docs/guides/models-intro#legacy-models-3)
- [api-reference/api-overview](https://platform.minimax.io/docs/api-reference/api-overview)
- [api-reference/image-generation-t2i](https://platform.minimax.io/docs/api-reference/image-generation-t2i)
- [api-reference/text-openai-api](https://platform.minimax.io/docs/api-reference/text-openai-api)
- [api-reference/file-management-upload](https://platform.minimax.io/docs/api-reference/file-management-upload)
- [guides/mcp-guide](https://platform.minimax.io/docs/guides/mcp-guide)
- [guides/token-plan-mcp-guide](https://platform.minimax.io/docs/guides/token-plan-mcp-guide)
- [token-plan/intro](https://platform.minimax.io/docs/token-plan/intro)
- [guides/pricing-token-plan](https://platform.minimax.io/docs/guides/pricing-token-plan)
- [guides/pricing-paygo](https://platform.minimax.io/docs/guides/pricing-paygo)
- [guides/pricing-speech](https://platform.minimax.io/docs/guides/pricing-speech)
- [guides/pricing-video](https://platform.minimax.io/docs/guides/pricing-video)
- [guides/rate-limits](https://platform.minimax.io/docs/guides/rate-limits)
- Local MCP server (ground truth for async video pattern): `G:\Github\Testing-Claude-Minimax-Mcp\minimax-mcp-server\server.py`