# Admin Gateway — Competitive Analysis

**Scope:** products comparable to the user's local Admin Gateway (a Python proxy on `127.0.0.1:48217` that forwards Claude Desktop traffic to MiniMax via the Anthropic-compatible API). Each product was reviewed against the same checklist: caching, rate-limiting, cost tracking, audit logs, fallbacks, retries, multi-tenant keys, admin UI, observability (OTel/Prom), PII redaction, guardrails, BYOK, virtual keys, spend caps. Every claim cites the URL it came from.

## 1. LiteLLM Proxy (BerriAI)

The OSS reference gateway in this category. Single Python process plus optional Postgres DB.

| Feature | Status | Source |
|---|---|---|
| Virtual keys (`sk-...`) | ✅ `/key/generate`, key block/unblock, expiry, model restrictions, key rotation with grace period, schedule auto-rotation | https://docs.litellm.ai/docs/proxy/virtual_keys |
| Rate limits per key | ✅ `tpm_limit`, `rpm_limit`, `max_parallel_requests` per key, team, user | https://docs.litellm.ai/docs/proxy/users |
| Spend tracking | ✅ Per key / user / team via `/key/info`, `/user/info`, `/team/info`; USD auto-calculated from `model_prices_and_context_window.json` | https://docs.litellm.ai/docs/proxy/virtual_keys#spend-tracking |
| Model aliasing | ✅ `model_name` group → many deployments; alias map on key (`"gpt-3.5-turbo": "my-free-tier"`); router `model_group_alias` | https://docs.litellm.ai/docs/proxy/configs |
| Fallbacks | ✅ `litellm_settings.fallbacks`, `context_window_fallbacks`, `allowed_fails` cooldown | https://docs.litellm.ai/docs/proxy/configs#load-balancing |
| Retries | ✅ `litellm_settings.num_retries`, per-model in router | same |
| Caching | ✅ Redis / in-memory, simple + semantic (Qdrant/Redis), per-key namespaces | https://docs.litellm.ai/docs/proxy/caching |
| Audit logs | ✅ Enterprise: full admin action log | https://docs.litellm.ai/docs/proxy/multiple_admins |
| Multi-tenant routing | ✅ Teams, Organizations, Users with inheritance | https://docs.litellm.ai/docs/proxy/virtual_keys |
| RBAC | ✅ Roles `proxy_admin`, `proxy_admin_viewer`, `org_admin`, `internal_user`, `internal_user_viewer`, `team`, `customer` | https://docs.litellm.ai/docs/proxy/access_control |
| Spend caps | ✅ `max_budget`, `budget_duration` (e.g. "10d"), soft alerts and hard blocks; `temp_budget_increase` | https://docs.litellm.ai/docs/proxy/virtual_keys |
| Admin UI | ✅ Built-in web UI on port 4000 (Swagger + key/user/team pages) | https://docs.litellm.ai/docs/proxy/ui |
| OpenTelemetry / Prom | ✅ `success_callback: ["langfuse", "prometheus"]`, dynamic callback config | https://docs.litellm.ai/docs/proxy/dynamic_logging |
| PII redaction | ✅ Built-in `presidio` guardrail with per-entity actions and score thresholds | https://docs.litellm.ai/docs/proxy/guardrails/quick_start |
| Guardrails | ✅ 20+ integrations: Aporia, Lakera, Presidio, Bedrock, Azure Content Safety, Pillar, custom Generic Guardrail API; `pre_call` / `during_call` / `post_call` / `logging_only` modes | same |
| BYOK | ✅ `litellm_credential_name` + `credential_list` with `os.environ/` references | https://docs.litellm.ai/docs/proxy/configs#centralized-credential-management |
| Observability sinks | ✅ Datadog, Langfuse, Prometheus, S3, BigQuery, OpenTelemetry exporter | https://docs.litellm.ai/docs/proxy/dynamic_logging |

## 2. Portkey AI Gateway

Hosted plus OSS gateway (`npx @portkey-ai/gateway`). Now branded as Palo Alto Networks Prisma AIRS AI Gateway.

| Feature | Status | Source |
|---|---|---|
| Caching | ✅ Simple (exact match) + Semantic (cosine, default 0.95 threshold, Milvus / Pinecone, OpenAI/Google/Vertex embeddings); per-target TTL, force-refresh, namespaces | https://docs.portkey.ai/docs/product/ai-gateway/cache-simple-and-semantic |
| Rate limits | ✅ Hourly / daily / per-minute limits on requests or tokens; per-workspace budget caps | https://docs.portkey.ai/docs/product/model-catalog/integrations#3-budget-%26-rate-limits |
| Fallbacks | ✅ JSON config strategy with prioritized targets, `on_status_codes`, composable with load balancing / conditional routing | https://docs.portkey.ai/docs/product/ai-gateway/fallbacks |
| Retries | ✅ Up to 5 attempts, configurable status codes (default `[429,500,502,503,504,529]`), exponential backoff (1/2/4/8/16s), honors provider `Retry-After` capped at 60s | https://docs.portkey.ai/docs/product/ai-gateway/automatic-retries |
| Circuit breaker | ✅ Per-strategy circuit protection | https://docs.portkey.ai/docs/product/ai-gateway/circuit-breaker |
| Load balancing | ✅ Across API keys to counter rate limits | https://docs.portkey.ai/docs/product/ai-gateway/load-balancing |
| Conditional routing | ✅ Route by custom condition checks | https://docs.portkey.ai/docs/product/ai-gateway/conditional-routing |
| Canary testing | ✅ | https://docs.portkey.ai/docs/product/ai-gateway/canary-testing |
| Request timeout | ✅ | https://docs.portkey.ai/docs/product/ai-gateway/request-timeouts |
| Cost tracking | ✅ Logs/analytics dashboard with spend, token usage per request | https://portkey.ai/docs |
| Audit logs | ✅ Logs dashboard with status column, trace ID filter | https://docs.portkey.ai/docs/product/ai-gateway/fallbacks |
| Multi-tenant keys | ✅ Workspaces, org-scoped configs | https://portkey.ai/docs |
| Admin UI | ✅ Cloud console + Model Catalog | https://portkey.ai/docs |
| Virtual keys | ✅ Configs (e.g. `pc-cache-xxx`) passed via `x-portkey-config` header | https://docs.portkey.ai/docs/product/ai-gateway/configs |
| BYOK | ✅ Pass provider key via `Authorization` plus Portkey key via `x-portkey-api-key`; multi-provider routing | https://portkey.ai/docs |
| Observability | ✅ Logs + Analytics, OpenTelemetry-compatible exports | https://portkey.ai/docs |
| Guardrails / PII | ✅ Through partner integrations (Aporia, Patronus, etc.); ISO 27001, SOC 2, HIPAA, GDPR | https://portkey.ai/docs |

## 3. Cloudflare AI Gateway

Edge-hosted gateway that sits in front of provider APIs. Free on all plans.

| Feature | Status | Source |
|---|---|---|
| Caching | ✅ Edge cache, per-request TTL (60s to 1 month), custom cache key header, skip-cache header; SHA-256 of provider + endpoint + model + auth + body | https://developers.cloudflare.com/ai-gateway/features/caching/ |
| Rate limiting | ✅ Fixed or sliding window, configurable interval + technique, 429 response | https://developers.cloudflare.com/ai-gateway/features/rate-limiting/ |
| Retries + fallbacks | ✅ "Dynamic routing" with model fallback chains | https://developers.cloudflare.com/ai-gateway/features/dynamic-routing/ |
| Custom providers | ✅ Workers AI, Anthropic, Gemini, OpenAI, Replicate, Groq, any OpenAI-compatible endpoint | https://developers.cloudflare.com/ai-gateway/usage/providers/ |
| Analytics | ✅ Request count, tokens, cost, error rate, latency, model breakdowns | https://developers.cloudflare.com/ai-gateway/observability/analytics/ |
| Logging | ✅ Request/response logs, error logs | https://developers.cloudflare.com/ai-gateway/observability/logging/ |
| BYOK | ✅ Your provider API key in `Authorization` header | https://developers.cloudflare.com/ai-gateway/ |
| Virtual keys | ❌ Not a multi-tenant gateway; the "gateway" is a single account-level resource identified by Account ID | https://developers.cloudflare.com/ai-gateway/ |
| Admin UI | ✅ Cloudflare dashboard under **AI → AI Gateway** | https://developers.cloudflare.com/ai-gateway/ |
| PII redaction / guardrails | ❌ Not provided | — |
| Spend caps / multi-tenant | ❌ No per-key spend controls (rate limiting only) | — |
| Observability (OTel/Prom) | ⚠️ Logs/analytics in dashboard; exportable via Workers Analytics Engine; no native OTel endpoint documented | https://developers.cloudflare.com/ai-gateway/observability/analytics/ |

## 4. OpenRouter

Public hosted model router (not really a gateway you self-host).

| Feature | Status | Source |
|---|---|---|
| Per-key API keys | ✅ Providable with `limit`, `limit_reset`, `limit_remaining` (credit cap per key) | https://openrouter.ai/docs/api/reference/limits |
| Account-level credit limits | ✅ Returns 402 when exhausted | same |
| Rate limits | ✅ Free-model RPM/RPD caps; Cloudflare DDoS protection; 429 with `Retry-After` | same |
| Auto Router | ✅ `openrouter/auto` ranks models by trailing-7-day share-of-spend for ~30 task types; `cost_tier: low|medium|high|xhigh|max`; `allowed_models` / `excluded_models` wildcards | https://openrouter.ai/docs/features/model-routing |
| Fallbacks | ✅ Provider fallback routing auto-retries other providers for the same model; explicit fallback models for whole-model failover | https://openrouter.ai/docs/api/reference/limits |
| Provider routing (BYOK with provider preferences) | ✅ `provider` object selects order / allowlist / data policy / quantization / max price | https://openrouter.ai/docs/guides/routing/provider-selection |
| Data policy / guardrails | ✅ Per-provider retention table, opt-out of providers that train on prompts; ZDR (zero data retention) filtering | https://openrouter.ai/docs/features/privacy-and-logging |
| App-level routing | ✅ Settings page (privacy, routing) drive account defaults | https://openrouter.ai/settings/routing |
| Cost tracking | ✅ `usage`, `usage_daily`, `usage_weekly`, `usage_monthly`, `byok_usage_*` from `GET /api/v1/key` | https://openrouter.ai/docs/api/reference/limits |
| BYOK | ✅ `include_byok_in_limit` flag plus provider-specific keys | same |
| Admin UI | ✅ Web dashboard with privacy and routing pages | https://openrouter.ai/settings/privacy |
| Caching | ❌ Not a feature | — |
| Audit logs / per-user RBAC | ⚠️ Logs are per-request; no enterprise RBAC; enterprise in-region routing (EU/US) on request | https://openrouter.ai/docs/features/privacy-and-logging |
| Observability | ⚠️ Per-request metadata + `X-OpenRouter-Metadata`; no OTel | https://openrouter.ai/docs/guides/features/router-metadata |
| PII redaction / guardrails | ❌ Provider-side only; OpenRouter exposes data policy filtering | https://openrouter.ai/docs/features/privacy-and-logging |

## 5. TrueFoundry AI Gateway

Enterprise SaaS / hybrid / self-hosted LLM gateway.

| Feature | Status | Source |
|---|---|---|
| Unified API | ✅ OpenAI-compatible `/chat/completions` for 1000+ models | https://www.truefoundry.com/docs/ai-gateway |
| Caching | ✅ Semantic caching | https://www.truefoundry.com/docs/ai-gateway/caching |
| Load balancing + fallbacks | ✅ Virtual models by weight/latency/priority with automatic retries | https://www.truefoundry.com/docs/ai-gateway/virtual-model |
| Rate limiting | ✅ Per-user, per-model, per-application | https://www.truefoundry.com/docs/ai-gateway/ratelimiting |
| Budgets / cost tracking | ✅ Per-team, enforce spend limits | https://www.truefoundry.com/docs/ai-gateway/budget-limiting-v2 |
| Guardrails (incl. PII) | ✅ PII, prompt injection, content moderation, custom policies | https://www.truefoundry.com/docs/ai-gateway/guardrails-overview |
| Observability | ✅ OpenTelemetry-compliant metrics, traces, request logs | https://www.truefoundry.com/docs/ai-gateway/analytics |
| Prompt management | ✅ Versioned prompts, built-in playground | https://www.truefoundry.com/docs/ai-gateway/prompt-management |
| RBAC / API keys | ✅ RBAC + scoped keys for users, teams, apps | https://www.truefoundry.com/docs/ai-gateway/gateway-access-control |
| BYOK | ✅ Provider credential storage per integration | https://www.truefoundry.com/docs/ai-gateway |
| MCP / agent support | ✅ MCP registry, agent registry, skills registry | same |

## 6. Kong AI Gateway / Tyk / Envoy AI Gateway (enterprise gateway AI extensions)

**Kong AI Gateway** (`https://docs.konghq.com/gateway/latest/ai-gateway/`): universal API via AI Proxy + AI Proxy Advanced; semantic caching + semantic routing; rate limiting; guardrails (AI Prompt Guard, AI Semantic Prompt Guard, AI PII Sanitizer 20 PII categories × 9 languages, AI Azure Content Safety, AI AWS Guardrails, AI GCP Model Armor, AI Lakera Guard, AI Custom Guardrail, AI Semantic Response Guard); data governance allow/deny lists; AI Prompt Template / Decorator; load balancing (consistent hashing, lowest-latency, usage-based, round-robin, semantic); retry + fallback; LLM cost control (AI Compressor, RAG Injector, semantic load balancing); audit log + LLM metrics; OpenTelemetry Gen AI OTLP spans + metrics; metering/billing; Konnect config-store secrets.

**Tyk AI Gateway / Tyk AI Studio** (`https://tyk.io/learning-center/ai-gateway/`): Tyk AI Studio for centralized AI governance; rate limiting to prevent runaway token usage; real-time cost/usage/budget dashboards with team and project-level chargeback; OpenTelemetry-ready observability; OAuth/OIDC auth; content filtering; PII scrubbing; audit trails; model registries; approval workflows.

**Envoy AI Gateway** (`https://gateway.envoyproxy.io/`, `https://github.com/envoyproxy/ai-gateway`): extProc-based AI gateway running on Envoy; native OpenTelemetry AI spans; routing by request body / header / model name; token-based rate limiting; provider credential management (BYOK) for OpenAI, Anthropic, AWS Bedrock, Azure OpenAI, GCP Vertex; model aliases, upstream failover, weighted routing; composable with Envoy RBAC, TLS, mTLS, JWT.

## 7. ZenMux

Unified LLM platform offering OpenAI, Anthropic, and Vertex-compatible endpoints. `https://zenmux.ai/docs`

- Unified API for 200+ LLM models
- Provider routing (`https://zenmux.ai/guide/advanced/provider-routing.html`)
- Model routing (`https://zenmux.ai/guide/advanced/model-routing.html`)
- Fallback models (`https://zenmux.ai/guide/advanced/fallback.html`)
- Prompt caching (`https://zenmux.ai/guide/advanced/prompt-cache.html`)
- Streaming, multimodal, structured output, tool calls, reasoning models
- Anthropic-compatible `/api/anthropic`, OpenAI-compatible `/api/v1`, Vertex-compatible `/api/vertex-ai`
- "AI Model Insurance" feature for hallucination risk
- No explicit docs page found for: RBAC, admin UI, audit logs, OTel/Prom metrics, virtual keys, PII redaction. Not confirmed.

## 8. CCPG — Claude Code Provider Gateway

Open-source Tauri desktop app + local daemon. `https://github.com/danielalves96/claude-code-provider-gateway`, https://ccpg.live/docs

| Feature | Status | Source |
|---|---|---|
| Local proxy | ✅ Anthropic-compatible on `:49250`, OpenAI-compatible on same port, plus panel UI on `:6767` (Docker) | README |
| Provider catalog | ✅ 40+ providers: OpenAI Account OAuth, GitHub Copilot, Kilo, Cline, OpenRouter, DeepSeek, NVIDIA NIM, Kimi, Gemini, Groq, xAI, Mistral, Ollama, LM Studio, llama.cpp, Minimax, GLM, etc. | README |
| Multi-provider aggregation | ✅ `--all` flag exposes one unified model catalog to Claude Code | README |
| Model tier routing | ✅ Maps `opus` / `sonnet` / `haiku` to user-chosen models | README |
| Model Chains (fallback) | ✅ User-defined waterfall: retries on rate limit, network error, empty stream; first-token + total stream timeouts | README |
| Provider safeguards | ✅ Per-provider concurrency / rate limits; client cancel aborts upstream | README |
| Secrets storage | ✅ AES-256-GCM encrypted store for API keys / OAuth tokens / gateway auth token | README |
| Request history | ✅ Local UI: prompt preview, response preview, token count, latency, provider errors | README |
| Token savers | ✅ RTK tool-result compression, Caveman terse mode | README |
| Outbound HTTP proxy | ✅ Configurable in Settings | README |
| Parallel sessions | ✅ Per-session isolation with heartbeats | README |
| Caching | ❌ None | — |
| Rate limits per key | ❌ Single gateway token, no per-key rate limits | — |
| Cost tracking / spend caps | ❌ None | — |
| Audit logs / OTel | ❌ Local history only | — |
| PII redaction / guardrails | ❌ None | — |
| Admin UI | ✅ Desktop panel, but single-user | README |
| Virtual keys | ❌ One gateway token for the daemon | — |
| BYOK | ✅ Each provider has its own key (or OAuth) in the encrypted store | README |

## 9. claude-3p-ollama-proxy

Minimal Node.js compatibility shim. `https://github.com/francescogruner/claude-3p-ollama-proxy`

- Sits between Claude Desktop's third-party-gateway mode and Ollama Cloud (`https://ollama.com/v1/messages`)
- Exposes Anthropic-style model aliases (`claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001`) and rewrites them to Ollama model IDs
- ~1 file `server.js` using only Node built-ins
- `OLLAMA_API_KEY` env var; optional `MODEL_SONNET` / `MODEL_HAIKU` / `DEFAULT_MODEL` overrides
- Endpoints: `/v1/models`, `/v1/messages`, `/health`
- **Lacks**: caching, rate-limiting, cost tracking, audit logs, fallbacks, retries, multi-tenant keys, admin UI, observability, PII redaction, guardrails, BYOK concept, virtual keys, spend caps, even streaming reliability — explicitly marked "experimental"

This is the closest peer to the user's local Admin Gateway in scope and is the natural upgrade target if Anthropic compatibility stays required.

## 10. Anthropic Prompt Router / AWS Bedrock Model Router / Azure AI Foundry routing

- **Anthropic Prompt Router** (beta): server-side router that picks the best Claude model for a prompt based on cost/quality; documented in release notes and the ZenMux ClaudeCode integration guide (`https://zenmux.ai/best-practices/claude-code.html`).
- **AWS Bedrock**: inference profiles / prompt routing across Claude, Llama, Nova, etc. (`https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html`).
- **Azure AI Foundry**: model router for Foundry-hosted models with enterprise governance (RBAC, virtual network, customer-managed keys); Foundry's AI Gateway described at `https://learn.microsoft.com/en-us/azure/ai-foundry/`.

These are platform-internal routing layers with full enterprise RBAC, audit, OTel, guardrails, and BYOK.

## Feature matrix across products

| Feature | Admin Gateway (user) | LiteLLM | Portkey | CF AI GW | OpenRouter | TrueFoundry | Kong AI GW | Tyk AI Studio | Envoy AI GW | ZenMux | CCPG | 3p-ollama-proxy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Caching | — | ✅ simple+semantic | ✅ simple+semantic | ✅ exact, custom-key | — | ✅ semantic | ✅ semantic | ⚠️ via OTel+plugins | ❌ (delegated) | ✅ prompt cache | ❌ | ❌ |
| Rate limits | — | ✅ per-key | ✅ per-workspace | ✅ fixed/sliding | ✅ per-key + free-tier caps | ✅ per user/model/app | ✅ plugin | ✅ via APIM | ✅ via Envoy filter | ❓ | ✅ per provider | ❌ |
| Cost tracking | — | ✅ USD | ✅ analytics | ✅ cost view | ✅ per-key usage | ✅ budgets | ✅ metering | ✅ cost dashboards | ⚠️ via metrics | ❓ | ❌ | ❌ |
| Audit logs | — | ✅ Ent. | ✅ logs | ✅ logs | ⚠️ request only | ✅ logs | ✅ audit log plugin | ✅ audit trails | ⚠️ access logs | ❓ | ✅ local only | ❌ |
| Fallbacks | — | ✅ | ✅ priority list | ✅ dynamic routing | ✅ provider + model | ✅ virtual model | ✅ LB plugin | ✅ | ✅ weighted | ✅ | ✅ Model Chains | ❌ |
| Retries | — | ✅ num_retries | ✅ exponential + Retry-After | ✅ dynamic routing | ✅ auto provider fallback | ✅ | ✅ LB plugin | ✅ | ✅ | ❓ | ✅ chain retry | ❌ |
| Multi-tenant keys | — | ✅ teams/orgs | ✅ workspaces | ❌ | ✅ per-key credit caps | ✅ teams+apps | ✅ RBAC | ✅ | ⚠️ via JWT | ❓ | ❌ single gateway token | ❌ |
| Admin UI | — | ✅ web | ✅ cloud console | ✅ dashboard | ✅ web | ✅ dashboard | ✅ Konnect | ✅ Tyk AI Studio | ❌ (YAML/IaC) | ❓ | ✅ desktop panel | ❌ |
| OTel / Prom | — | ✅ callbacks | ✅ exports | ⚠️ logs | ⚠️ metadata only | ✅ OTel-compliant | ✅ Gen AI OTLP | ✅ OTel ecosystem | ✅ AI semantic spans | ❓ | ❌ | ❌ |
| PII redaction | — | ✅ Presidio | ✅ partners | ❌ | ❌ | ✅ | ✅ AI PII Sanitizer | ✅ scrubbing | ❌ (delegated) | ❓ | ❌ | ❌ |
| Guardrails | — | ✅ 20+ integrations | ✅ partners | ❌ | ⚠️ data-policy filter only | ✅ | ✅ 10+ plugins | ✅ policies | ❌ (delegated) | ❓ | ❌ | ❌ |
| BYOK | ✅ env | ✅ credential_name | ✅ `x-portkey-provider` | ✅ upstream auth | ✅ include_byok_in_limit | ✅ | ✅ Konnect config store | ✅ | ✅ | ❓ | ✅ per-provider key | ✅ env |
| Virtual keys | — | ✅ `sk-...` | ✅ `pc-...` configs | ❌ | ✅ per-key limit | ✅ scoped keys | ✅ key-auth plugin | ✅ key auth | ✅ JWT | ❓ | ❌ | ❌ |
| Spend caps | — | ✅ max_budget | ✅ budget limits | ❌ | ✅ key limit + account | ✅ budgets | ✅ metering | ✅ budgets | ❌ | ❓ | ❌ | ❌ |

## What every serious gateway has that the user's doesn't

Every product in this audit except `claude-3p-ollama-proxy` ships four controls the user's local Admin Gateway has not implemented:

1. **per-key rate limiting**
2. **cost / spend tracking with hard caps**
3. **an admin UI or persistent request log (audit)**
4. **at least one guardrail hook (PII redaction or data-policy filtering)**

Adding OpenTelemetry/callback-based observability is also universal in LiteLLM, Portkey, TrueFoundry, Kong, Tyk, and Envoy. The most natural upgrade path for the user's stack is therefore to keep the single-user `127.0.0.1:48217` proxy but layer in:

- (a) a lightweight SQLite spend log keyed by request,
- (b) a fixed RPM cap to prevent runaway MiniMax bills,
- (c) Presidio-based PII redaction on prompts before they leave the host, and
- (d) basic OTel export to a local OTLP collector

All four are supported by LiteLLM's OSS edition out of the box and represent the de facto baseline of this product category.