# GOAL — CLEVER-JARVIS-001

**Defined:** 2026-08-31  
**Repository:** `rotprods/Clever-Agent`  
**Goal class:** multi-runtime personal AI platform / agentic operating system

## Mission

Build a production-grade **real JARVIS**: one coherent personal AI that can perceive, remember, reason, learn, communicate and act across the user's devices and channels while remaining local-first, user-owned, auditable and safe.

The system MUST preserve and unify **100% of the materially usable capabilities** present in the pinned upstream snapshots of:

1. `open-jarvis/OpenJarvis`
2. `openclaw/openclaw`
3. `BasedHardware/omi`
4. `farzaa/clicky`

The union is a floor, not a ceiling. After parity, Clever-Agent adds new capabilities required for a cohesive JARVIS experience: unified identity, shared goals, cross-device continuity, permissioned computer control, wake-word/barge-in voice interaction, proactive planning, evidence-backed memory and continuous upstream synchronization.

## Product outcome

A user should experience one assistant rather than four systems:

- Speak from macOS, phone or wearable and reach the same identity and memory.
- Ask about what was recently heard or seen and retrieve attributable episodic context.
- Ask the assistant to point to something on-screen, explain it, or perform an allowed action.
- Continue the same task from Telegram/WhatsApp/Slack/Web UI/device nodes without memory fragmentation.
- Run useful tasks locally when hardware permits, with explicit cloud fallback policies.
- Schedule and monitor long-running goals and receive proactive updates.
- Improve model/tool/agent routing from traces without silently weakening safety or privacy.
- Operate offline for the local capability subset and degrade gracefully when providers fail.

## Hard invariants

### I-01 — Capability parity
No upstream capability may disappear silently. Every discovered capability receives a canonical ID, owner, adapter mapping, parity test and evidence record. `100% parity` means `verified_capabilities == in_scope_capabilities`, not a subjective claim.

### I-02 — Upstream provenance
Every imported, vendored or adapted component retains source repository, pinned commit, license and required notices. Upstream code is never copied without provenance.

### I-03 — Local-first intelligence
Local inference is preferred when it satisfies the task's quality, latency, privacy and resource policy. Cloud inference is a configurable fallback, not an architectural requirement.

### I-04 — One identity, explicit session boundaries
All channels and devices resolve to canonical user/device/session identities. Group chats, third parties and shared environments remain isolated by policy.

### I-05 — User-owned memory
Memory is exportable, inspectable and deletable. Raw ambient capture is not treated as permanent memory by default; retention is policy-controlled and derived memories preserve provenance.

### I-06 — Consent-aware perception
Microphone, screen, camera, location and wearable capture are permission-gated and visibly controllable. Ambient capture never bypasses operating-system permissions or user policy.

### I-07 — Untrusted input by default
Messages, webpages, documents, screenshots, tool output and remote device events are untrusted data. They cannot grant themselves permissions or override system policy.

### I-08 — Least-privilege action
All side effects pass through a policy broker. High-risk actions require stronger authorization than read-only or reversible actions. Credentials are never exposed to model context unless explicitly required and scoped.

### I-09 — Sandboxed execution
Arbitrary code, shell commands, browser automation and third-party skills run inside declared trust boundaries. Host execution is opt-in and auditable.

### I-10 — Durable truth
Git + machine-readable state + append-only run/decision/evidence ledgers are the source of continuity. Chat memory is never the sole source of project state.

### I-11 — Evidence before DONE
No checkpoint, capability or release may be marked complete from prose alone. Completion requires test output and evidence paths.

### I-12 — Failure-aware design
Provider, network, device and process failure must degrade gracefully. No component may claim success while dropping audio, events, memory writes or side effects.

### I-13 — No single-language rewrite mandate
The system preserves mature upstream runtimes. Rewrites require measured benefit, parity proof and an ADR.

### I-14 — Security cannot be optimized away
Learning, self-modification, prompt optimization and routing may not weaken permission gates, auditability, privacy policy or sandbox boundaries.

## Explicit non-goals

- Claiming AGI, consciousness or human-equivalent cognition.
- Merging all upstream repositories into one monolithic language/runtime.
- Reproducing every upstream UI pixel-for-pixel when the capability is preserved through a superior unified surface.
- Shipping uncontrolled always-on recording.
- Treating raw chat history as a durable state database.
- Giving third-party plugins unrestricted host access.
- Replacing upstream implementations before parity baselines exist.

## Definition of Done

The goal is complete only when all of the following are true:

1. **Forensic inventory:** source trees, runtime surfaces, commands, APIs, plugins, device capabilities and tests from all four pinned upstream commits are inventoried.
2. **Parity denominator:** the generated capability ledger contains every in-scope upstream capability with source evidence.
3. **Canonical contracts:** identity, device, session, event, memory, trace, goal, capability, permission, tool-call and action-result schemas are versioned.
4. **Kernel:** the Clever JARVIS kernel boots, exposes capability discovery, routes canonical events, persists policy decisions and maintains durable state.
5. **OpenJarvis integration:** local/cloud engines, agent families, memory backends, traces, learning, tools, security, telemetry and scheduler are callable through canonical contracts.
6. **OpenClaw integration:** gateway, channels, model providers, sessions, nodes, media, browser/exec/search tools, skills/plugins, workflows, pairing and automation are preserved through the unified control plane.
7. **Omi integration:** desktop/mobile/wearable capture, BLE, STT, diarization/speaker identity, conversation processing, memories, action items, chat/app/MCP surfaces and supported device SDK capabilities are preserved.
8. **Clicky integration:** macOS menu-bar embodiment, PTT, screen capture, multi-monitor perception, TTS, transcription provider abstraction, visual pointing/overlay and element localization are preserved.
9. **Unified memory:** working, episodic, semantic, procedural, profile and evidence memories have explicit retention/provenance semantics and can be queried across devices.
10. **Unified action system:** side effects use permission classes, idempotency keys, policy decisions and auditable results.
11. **Cross-device continuity:** the same goal can start on one supported surface and continue on another without losing canonical state.
12. **Offline mode:** a documented local subset works without cloud connectivity and fails closed where cloud-only capability is unavoidable.
13. **Learning loop:** traces can improve routing/skills/prompts under evaluation gates; production promotion requires measured improvement and no security regression.
14. **Security:** threat model, secret handling, sandbox tests, prompt-injection tests, device pairing tests and destructive-action authorization tests pass.
15. **Parity:** generated report shows 100% of in-scope capabilities VERIFIED, or an explicit user-approved waiver exists for each excluded capability.
16. **Upstream sync:** automated drift detection compares pinned upstreams to newer commits and opens a structured parity delta.
17. **Release evidence:** end-to-end scenarios, performance baselines, recovery tests and release manifest are reproducible on supported hardware.

## Required end-to-end acceptance scenarios

- **Desktop companion:** press/speak → transcribe → capture relevant display → reason → stream answer → speak answer → point to target UI element.
- **Ambient recall:** wearable/desktop conversation → diarized transcript → derived memory → later attributable retrieval.
- **Multichannel continuity:** begin goal on desktop → continue through a chat channel → return to desktop with the same canonical goal/session state.
- **Local-first routing:** disconnect cloud → local model handles supported query/tool path → telemetry records selected engine and degradation mode.
- **Provider failover:** active STT/model provider fails → bounded fallback occurs without false success or silent data loss.
- **Scheduled autonomy:** persistent agent executes a scheduled/monitoring goal, records trace/evidence and reports only when policy permits.
- **Computer action:** assistant proposes action → policy broker classifies → user authorization where required → tool executes idempotently → result/audit persisted.
- **Device trust:** new node pairs explicitly; unpaired remote device cannot issue privileged commands.
- **Prompt-injection resistance:** malicious channel/web/document content cannot elevate permissions or exfiltrate protected secrets.
- **Upstream parity regression:** remove/disable a mapped capability in a test branch → parity gate fails.

## Success criterion

`CLEVER-JARVIS-001` reaches DONE only when the system behaves as a single assistant and the generated evidence proves the capability union, not merely the existence of four embedded projects.
