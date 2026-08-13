As of August 10, 2026, Anthropic now officially supports third-party inference directly in Claude Desktop. This became generally available July 9, 2026. MiniMax M3 exposes an Anthropic-compatible API, including streaming, tool calls, images/video, token counting, and a 1-million-token context window. Those two pieces now fit together directly.

Claude Desktop → MiniMax M3: use this first

You should not need LiteLLM, OpenRouter, CCPG, a Cloudflare Worker, or another proxy for the first attempt.

Use:

Claude Desktop field	Value
Connection / Inference Provider	Gateway
Gateway Base URL	https://api.minimax.io/anthropic
Gateway API Key	your MiniMax API key
Authentication Scheme	x-api-key
Model	MiniMax-M3
Model discovery	Can be OFF
1M context	Enable if the GUI exposes it
Claude family/tier mapping	opus if the GUI asks for a family tier

That URL is important. Claude Desktop appends /v1/messages, producing MiniMax's documented endpoint:

https://api.minimax.io/anthropic/v1/messages

MiniMax documents its Anthropic-compatible base URL as exactly https://api.minimax.io/anthropic. Its model-list endpoint also explicitly requires the X-Api-Key header, which is why x-api-key is the correct Claude Desktop gateway authentication scheme.

Exact Windows GUI procedure
Update Claude Desktop first. The current third-party mode is part of the regular Claude Desktop application. On Windows, Anthropic specifically recommends the current .msix; Cowork requires the MSIX rather than the old legacy EXE installation.
Completely sign out or launch Claude before signing in. Anthropic's single-machine instructions specifically say you do not need to create/sign into an Anthropic account for this configuration.
In Claude Desktop open:
☰ → Help → Troubleshooting → Enable Developer Mode
Claude will restart. Now open:
Developer → Configure Third-Party Inference…
Select:
Inference Provider = Gateway
Enter:
Gateway Base URL
https://api.minimax.io/anthropic
Paste your MiniMax API token into:
Gateway API Key

Set:
Gateway Auth Scheme = x-api-key

Anthropic Desktop supports both bearer and x-api-key; MiniMax's documented Anthropic API uses X-Api-Key.

Manually add the model:
MiniMax-M3

Do not depend on automatic model discovery for this. Anthropic says Claude Desktop deliberately filters automatically discovered models whose IDs do not look like Claude model names. Explicit inferenceModels entries bypass that problem.

If the configuration screen gives you advanced model properties, use:

Model ID: MiniMax-M3

Display name: MiniMax M3

Supports 1M: Yes

MiniMax officially states M3 has a 1,000,000-token context window.

If it asks for an Anthropic family/tier, I would map it to Opus. That does not magically turn MiniMax into Opus; it simply tells Claude Desktop what model to substitute when its Code machinery refers internally to an opus family alias. Anthropic specifically provides anthropicFamilyTier for this gateway-model mapping.

Initially leave experimental MCP Tool Search disabled. Anthropic intentionally disables experimental beta request fields by default on third-party Desktop because some compatible APIs reject those extra Claude-specific fields. We want the most conservative MiniMax-compatible request surface for the first successful run.
Click Apply locally.
Claude restarts. The login/start screen should now offer the third-party configuration rather than forcing normal Anthropic authentication. Anthropic says that once provider + credentials are valid, you can skip Anthropic authentication and run with the configured inference provider.
Start a simple conversation first:
Respond with exactly: MiniMax M3 connection successful.
Then test agent/tool behavior:
Create a folder called minimax-claude-test and create README.md inside it containing the current model name and today's date.

That second test is important because a provider can work for plain text while breaking Claude Desktop's agent loop/tool calls. MiniMax says its Anthropic-compatible API fully supports tool_use and tool_result, which is exactly what we need.

How to verify it without a terminal

Anthropic built this into the GUI too.

Go to:

Help → Troubleshooting → Copy Managed Configuration Report

The report shows which inference provider was found and whether the credentials validated; secret values are redacted. Anthropic specifically recommends this as the verification procedure.

If it doesn't start, look at:

%LOCALAPPDATA%\Claude-3p\Logs\main.log

Anthropic identifies that as the Windows third-party Desktop log location.

This is much better than the old Claude Code workaround

You were remembering a real Anthropic mechanism.

Previously, Claude Code could be redirected using:

ANTHROPIC_BASE_URL

ANTHROPIC_AUTH_TOKEN

and MiniMax's instructions were:

ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic

with MiniMax-M3. MiniMax still documents that configuration today.

But there was a major distinction:

Claude Code CLI/extension reads those environment variables.

Claude Desktop does not.

Anthropic now explicitly says Desktop uses its separate third-party inference configuration, not ANTHROPIC_BASE_URL or normal settings.json.

That difference explains a lot of the circular/conflicting instructions people have been posting.

And there is independent evidence this technique works with non-Claude models

This isn't just theoretical documentation.

There are already current 2026 examples of users configuring Claude Desktop third-party inference with non-Anthropic models. One published configuration specifically uses a MiniMax model through the Claude-3P gateway mechanism; another working open-source Cloudflare gateway reports live tests with both MiniMax M3 and M2.7.

A current walkthrough also demonstrates Claude Desktop's GUI configuration with OpenCode/MiniMax by selecting Gateway, x-api-key, manually supplying the MiniMax model ID, and applying locally.

But your situation is simpler because MiniMax itself already speaks Anthropic format. I would only introduce a proxy if direct MiniMax access exposes a compatibility bug.

If direct MiniMax fails: then use a proxy

My fallback order would be:

Direct MiniMax → CCPG → small dedicated proxy → LiteLLM

CCPG is interesting specifically for you because it has a Windows desktop GUI, supports MiniMax, Anthropic-compatible endpoints, OpenAI-compatible endpoints, Ollama and LM Studio, and is explicitly intended to avoid requiring users to hand-manage Node/Rust/etc. Its repository describes the Windows desktop app as the primary path.

But I would not install it yet.

We now have an official Claude Desktop gateway UI and a native MiniMax Anthropic endpoint. Adding a proxy prematurely gives us another moving part to debug.

Windsurf / Cascade / Devin situation

There has been a substantial 2026 product change here too.

Current Windsurf documentation has largely moved into Devin Desktop. Cascade is now one of Devin Desktop's local agents alongside Devin Local.

Cascade's built-in BYOK is more restrictive

Windsurf/Devin does officially have BYOK, but the documented BYOK mechanism is presently for selected models/providers, particularly Anthropic Claude models. Their changelog specifically describes supplying an Anthropic API key to unlock Claude BYOK models in Cascade.

I found no official Windsurf/Devin documentation saying that Cascade's normal BYOK box lets you replace Anthropic's endpoint with api.minimax.io.

So I would not put your MiniMax key in Cascade's Anthropic BYOK field and expect it to work. It is likely talking to an endpoint controlled by Windsurf/Devin or Anthropic rather than honoring an arbitrary Anthropic-compatible base URL.

But Devin Desktop now has a better workaround

Devin Desktop officially supports ACP — Agent Client Protocol.

That means you can run third-party coding agents inside Devin Desktop's graphical Agent Command Center, including:

Claude Agent
Codex
OpenCode
Gemini
custom ACP agents

The external agent performs the work but Devin Desktop remains the GUI.

This is probably the correct route for your MiniMax inside Devin/Windsurf requirement.

We can configure Claude Agent/Claude Code → MiniMax M3 using MiniMax's officially documented Anthropic endpoint, then expose that Claude agent through ACP inside Devin Desktop.

So you still interact with the desktop GUI, rather than sitting in a command window.

That is considerably cleaner than trying to trick Cascade's hard-coded BYOK implementation.

The setup priority I recommend
Application	MiniMax M3 BYOK approach	Status
Claude Desktop	Direct third-party Gateway → MiniMax Anthropic API	Do this now — strongest route
Claude Code Desktop/Code tab	Same Claude Desktop 3P configuration	Should inherit gateway configuration
Devin Desktop	Claude Agent/another agent through ACP using MiniMax	Official extensibility route
Windsurf/Cascade	Native BYOK doesn't document arbitrary MiniMax endpoints	Don't force it yet
Proxy	CCPG/LiteLLM/etc.	Fallback only

One limitation on my side: I cannot see your actual Windows C:\Private or G:\Private drive from this session, so I cannot safely locate or copy the MiniMax secret for you. I also don't want you posting the key into chat. Keep the actual key local and paste it directly into Claude Desktop's Gateway API Key box.

The biggest finding is that we probably don't need the workaround we were searching for earlier anymore. Anthropic added the missing functionality directly to Claude Desktop in 2026, and MiniMax M3 now supplies the matching Anthropic-compatible API.

If you want, I can next work through the exact Devin Desktop/Windsurf GUI + ACP arrangement for MiniMax M3, including the least-CLI method and whether we can package the setup so you just select “MiniMax M3” from Devin Desktop's agent selector.