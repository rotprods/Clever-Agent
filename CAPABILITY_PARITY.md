# Capability Parity Contract

## Meaning of “100%”

`100%` is a generated, evidence-backed ratio:

```text
verified in-scope capabilities / total discovered in-scope capabilities
```

This document is a **seed taxonomy**, not the final denominator. CP01 must scan the pinned upstream trees, docs, CLI/API surfaces, registries, plugins, device commands and tests to generate the exhaustive ledger.

A capability is VERIFIED only when all fields exist:

- canonical capability ID
- upstream source + pinned commit
- source evidence path/symbol/command
- native owner/runtime
- Clever adapter mapping
- parity test
- test result
- evidence artifact
- availability/degradation semantics

## State machine

`DISCOVERED → MAPPED → IMPLEMENTED → TESTED → VERIFIED`

Other terminal states require explicit justification: `OUT_OF_SCOPE_WITH_WAIVER`, `UPSTREAM_DEAD`, `BLOCKED`.

## Seed capability families

| Canonical family | Upstream | Capability seeds | Initial state |
|---|---|---|---|
| `COG.MODELS` | OpenJarvis | model catalog, runtime discovery, hardware metadata, generation config | DISCOVERED |
| `COG.ENGINES` | OpenJarvis | Ollama, vLLM, SGLang, llama.cpp, MLX/compatible engines, cloud providers, fallback/health | DISCOVERED |
| `COG.AGENTS` | OpenJarvis | simple, orchestrator, ReAct, CodeAct/OpenHands, RLM, Claude Code, operative, monitor operative | DISCOVERED |
| `COG.SANDBOX` | OpenJarvis | Docker/Podman agent sandbox, mount security | DISCOVERED |
| `MEM.RETRIEVAL` | OpenJarvis | SQLite/FTS5, FAISS, ColBERTv2, BM25, hybrid RRF, chunking/ingest/context injection | DISCOVERED |
| `LEARN.TRACES` | OpenJarvis | trace capture/store/analyze, trace-driven routing, rewards, prompt/skill optimization surfaces | DISCOVERED |
| `OBS.TELEMETRY` | OpenJarvis | inference telemetry, aggregation, latency/throughput/energy/cost evaluation surfaces | DISCOVERED |
| `AUTO.SCHEDULER` | OpenJarvis | once/interval/cron scheduling, persistent runs, operative/monitor workflows | DISCOVERED |
| `SEC.GUARDRAILS` | OpenJarvis | secret/PII scanning, sensitive-file policy, audit/security events | DISCOVERED |
| `EXT.SKILLS_MCP` | OpenJarvis | tool registry, MCP layer, external/community skills and benchmarking | DISCOVERED |
| `API.OPENAI_COMPAT` | OpenJarvis | FastAPI/OpenAI-compatible model/chat server + streaming | DISCOVERED |
| `GW.CORE` | OpenClaw | long-lived Gateway, typed WebSocket requests/responses/events, health/presence | DISCOVERED |
| `GW.SESSIONS` | OpenClaw | isolated sessions, sender/workspace routing, agent streaming | DISCOVERED |
| `GW.CHANNELS` | OpenClaw | Telegram, WebChat and official/external channel plugin ecosystem including WhatsApp/Slack/Discord/Signal/iMessage/etc. | DISCOVERED |
| `GW.AUTH_PAIRING` | OpenClaw | device identity, challenge signing, pairing, tokens, loopback/remote trust rules | DISCOVERED |
| `GW.PROVIDERS` | OpenClaw | hosted/local/custom model providers and OAuth/provider auth | DISCOVERED |
| `GW.MEDIA` | OpenClaw | image/audio/video/document I/O, generation, playback, voice notes, TTS | DISCOVERED |
| `GW.NODES` | OpenClaw | macOS/iOS/Android/headless nodes, camera, screen, location, voice, device commands | DISCOVERED |
| `GW.TOOLS` | OpenClaw | browser automation, exec, sandbox, web search providers | DISCOVERED |
| `GW.AUTOMATION` | OpenClaw | cron, heartbeat, workflows/Lobster | DISCOVERED |
| `GW.PLUGINS` | OpenClaw | skills, plugins, channel/provider/runtime hooks, ClawHub ecosystem | DISCOVERED |
| `GW.UI` | OpenClaw | Control UI, WebChat, CLI/TUI, macOS/menu/mobile surfaces, Canvas/A2UI | DISCOVERED |
| `PER.AMBIENT_AUDIO` | Omi | continuous/device audio capture and live streaming | DISCOVERED |
| `PER.SCREEN` | Omi | desktop screen capture/observational context | DISCOVERED |
| `PER.STT` | Omi | live/batch STT, multiple codecs/languages, provider selection and bounded failover | DISCOVERED |
| `PER.DIARIZATION` | Omi | speaker diarization and speech-profile identity | DISCOVERED |
| `PER.CONVERSATIONS` | Omi | conversation finalization, summaries, action items and processing | DISCOVERED |
| `MEM.EPISODIC_OMI` | Omi | remembered conversations/screen context and AI chat over history | DISCOVERED |
| `DEVICE.BLE` | Omi | BLE protocol, packet framing, device connection/streaming | DISCOVERED |
| `DEVICE.WEARABLE` | Omi | nRF/Zephyr Omi hardware capture | DISCOVERED |
| `DEVICE.GLASS` | Omi | ESP32-S3 Omi Glass camera/audio surface | DISCOVERED |
| `CLIENT.MOBILE` | Omi | Flutter iOS/Android app and device control surfaces | DISCOVERED |
| `EXT.OMI_APPS` | Omi | webhook apps, chat tools, audio-streaming apps, REST APIs, MCP | DISCOVERED |
| `SDK.OMI` | Omi | Python, Swift, React Native and multi-language device protocol SDKs | DISCOVERED |
| `DESKTOP.MENUBAR` | Clicky | menu-bar-only macOS companion and floating panel | DISCOVERED |
| `VOICE.PTT` | Clicky | global push-to-talk, audio capture, live waveform/state machine | DISCOVERED |
| `VOICE.STT_CLICKY` | Clicky | pluggable AssemblyAI/OpenAI/Apple Speech transcription | DISCOVERED |
| `VISION.SCREEN_CLICKY` | Clicky | ScreenCaptureKit multi-monitor screenshots sent with user query | DISCOVERED |
| `VOICE.TTS_CLICKY` | Clicky | ElevenLabs TTS playback and response lifecycle | DISCOVERED |
| `EMBODY.OVERLAY` | Clicky | transparent non-activating cursor/response overlay across displays | DISCOVERED |
| `EMBODY.POINTING` | Clicky | model-generated point tags, coordinate mapping, element location and cursor animation | DISCOVERED |
| `SEC.PROXY_CLICKY` | Clicky | Cloudflare proxy keeps provider API keys out of app binary | DISCOVERED |
| `OBS.CLICKY` | Clicky | application usage analytics surface | DISCOVERED |

## Parity test requirements

Parity tests are behavioral. A function name or compiled module is insufficient.

Examples:

- Channel parity test sends/receives through a configured test channel adapter.
- STT parity test streams audio and validates semantic outcome/failover behavior.
- Pointing parity test verifies target coordinate mapping on multiple displays.
- Engine parity test exercises discovery, health, generate/stream and fallback.
- Memory parity test writes, retrieves and attributes a known memory across configured backends.
- Scheduler parity test survives process restart and preserves run state.
- Pairing parity test denies unpaired remote nodes and accepts approved identities.

## Anti-shortcuts

- Do not count a single wrapper endpoint as parity for an entire upstream family.
- Do not replace provider/plugin ecosystems with a hard-coded shortlist.
- Do not mark UI-dependent capabilities verified from unit tests alone.
- Do not call a capability “equivalent” without a parity test demonstrating the required behavior.
- Do not reduce the denominator to make the score reach 100%.
