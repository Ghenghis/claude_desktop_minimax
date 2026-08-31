> HISTORICAL DOCUMENT — superseded by README.md and docs/SAFETY_REVIEW.md.
> Do not run old watchdog, permission-bypass, process-kill or repair instructions.

# MiniMax Capability Gap Audit

## What MiniMax provides

MiniMax is not only a chat model backend. Its current platform surface includes:

- Text generation: native Anthropic-compatible Messages and OpenAI-compatible
  chat/Responses adapters, streaming, tools, multimodal input, reasoning.
- Speech: Speech 2.8 HD/Turbo, voice selection, speed/volume/pitch/emotion,
  cloning, voice design, streaming and async long text.
- Image: Image-01 text-to-image, aspect ratios, batch, prompt optimization,
  custom width/height and image/reference modes where account access supports it.
- Video: H3/Hailuo models, text-to-video, image-to-video, first/last frame,
  reference workflows, async create/query/file-retrieve.
- Music: generation and cover APIs (account eligibility is changing; new-user
  access is not assumed).
- Search and vision: available through MiniMax's Token Plan / coding-plan MCP
  (`web_search`, `understand_image`); they are not automatically provided by
  the Anthropic chat endpoint.
- Video Agent: template-based asynchronous videos through
  `/v1/video_template_generation` and query endpoint.
- Files: upload, list, retrieve, download, and delete are needed for robust
  voice/video/reference workflows.

## What is now wired for both chat UIs

Through `mini`:

- Official `minimax` MCP: speech, voice list, voice clone, voice design,
  playback, image, video, video query.
- Custom `minimax-media`: speech, image, video, music.
- `touchpoint`: accessibility/UIA/CDP interaction for Claude and Codex desktop
  UI testing.
- `winremote`: Windows inspection tools; Tier 2 and Tier 3 are disabled in the
  default registry.
- Windows-MCP and daves-tools orchestration remain available.

## Remaining gaps

1. Vision/search: **implemented** as the pinned `minimax-coding-plan` MCP;
   `understand_image` and `web_search` are both registered and verified via
   `mini ls minimax-coding-plan`.
2. Video Agent templates: create/query tools are now registered in
   `minimax-media`; live task submission remains intentionally uncalled because
   it is paid.
3. Files tools: list/retrieve/download are now registered with numeric-ID
   validation and controlled output paths. Upload/delete remain deferred until
   their purpose-specific account behavior is contract-tested.
5. Image advanced modes: expose width/height and references only after live API
   schema validation; do not advertise unsupported parameters.
6. Long-text speech: add async TTS and timestamp/subtitle retrieval; sync TTS
   is not sufficient for all-night jobs.
7. Music: keep behind an explicit capability check and return a clear
   account-access error; do not build core workflows around it.
8. Observability: capture task IDs, provider error codes, latency, output path,
   and retry state without logging credentials or prompt secrets.
9. UI parity: MCP tools appear in both clients, but native chat composers do
   not automatically gain custom buttons for every provider API. Claude and
   Codex can invoke tools conversationally; native picker controls require
   client support and cannot safely be patched by gateway configuration.

## Recommended completion order

1. Keep text gateways stable and model identity truthful.
2. Keep official MiniMax MCP isolated from the custom Python MCP dependency
   tree; MCP protocol major versions currently conflict.
3. Add vision/search/files/templates as a separate `minimax-extended` MCP,
   avoiding destabilization of the already healthy official server.
4. Add contract tests with mocked API responses for every endpoint before live
   tests. Live tests: voices/list free; one tiny speech/image only; video only
   with explicit approval.
5. Run the health harness after every change and after a clean reboot.

## Mainstream parity definition

A mainstream-quality setup does not mean exposing every API as a native button.
It means:

- correct model routing and visible model identity;
- tools discoverable in both clients;
- structured inputs and explicit capability errors;
- safe permission tiers;
- async task continuation after client restart;
- bounded retries and idempotency where possible;
- local artifact paths and metadata;
- health checks, restart policy, and logs;
- no secrets in client config or logs.

That is the target for the remaining implementation passes.
