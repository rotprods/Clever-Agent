# Target Architecture — Clever-Agent JARVIS

## Architectural decision

Use a **federated polyglot architecture** with a new Rust kernel and strict versioned contracts. Do not flatten four mature systems into a monolith.

## Runtime planes

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         HUMAN / ENVIRONMENT                          │
│ voice · screen · camera · chats · files · devices · wearable audio │
└───────────────┬──────────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────────┐
│  PERCEPTION & EMBODIMENT                                            │
│  Omi capture / wearable / mobile  +  Clicky macOS overlay / PTT    │
└───────────────┬──────────────────────────────────────────────────────┘
                │ canonical PerceptionEvents
┌───────────────▼──────────────────────────────────────────────────────┐
│  CLEVER JARVIS KERNEL (Rust)                                        │
│  identity · sessions · capability registry · event router           │
│  goals · policy broker · permission broker · audit · state machine  │
└──────┬──────────────────────┬───────────────────────┬────────────────┘
       │                      │                       │
┌──────▼──────────┐   ┌───────▼──────────┐   ┌──────▼────────────────┐
│ COGNITION       │   │ GATEWAY / I/O    │   │ MEMORY / LEARNING     │
│ OpenJarvis      │   │ OpenClaw         │   │ OpenJarvis + Omi      │
│ engines/agents  │   │ channels/nodes   │   │ traces + episodes     │
└──────┬──────────┘   └───────┬──────────┘   └──────┬────────────────┘
       │                      │                       │
       └──────────────┬───────┴───────────────┬──────┘
                      │ canonical ActionIntent │
               ┌──────▼────────────────────────▼─────┐
               │ TOOLS / ACTION EXECUTION             │
               │ browser · exec · MCP · device cmds   │
               │ sandbox · idempotency · policy gate  │
               └───────────────────────────────────────┘
```

## 1. Clever JARVIS kernel

New Rust workspace proposed under `kernel/`.

Responsibilities:

- Canonical identity for users, devices, channels, sessions and goals.
- Capability registry and runtime discovery.
- Canonical event envelope and event routing.
- Goal/task state machine.
- Policy and permission decisions.
- Idempotency for side effects.
- Durable audit/evidence pointers.
- Health/readiness and degradation state.
- Adapter lifecycle supervision.

The kernel is **not** an LLM framework and **not** a replacement for OpenJarvis or OpenClaw.

## 2. Canonical contracts

Proposed directories:

```text
contracts/
  proto/
    identity.proto
    events.proto
    capabilities.proto
    memory.proto
    goals.proto
    policy.proto
    actions.proto
    traces.proto
  jsonschema/
  generated/
```

Every cross-runtime message MUST carry:

```text
schema_version
message_id
correlation_id
causation_id
occurred_at
producer
user_id
session_id?
device_id?
goal_id?
classification
payload
provenance
```

Core event families:

- `PerceptionEvent`
- `ConversationTurn`
- `ScreenObservation`
- `TranscriptSegment`
- `MemoryCandidate`
- `MemoryStored`
- `GoalEvent`
- `CapabilityAnnouncement`
- `ToolCallRequested`
- `PolicyDecision`
- `ActionIntent`
- `ActionResult`
- `TraceEvent`
- `HealthEvent`
- `SecurityEvent`

## 3. Upstream adapters

```text
adapters/
  openjarvis/
  openclaw/
  omi/
  clicky/
```

Adapters translate canonical contracts to native APIs/events. They MUST NOT silently emulate missing behavior.

### OpenJarvis adapter

Owns cognition-facing integration:

- model catalog and hardware-aware engine discovery
- local/cloud inference backends
- agent registry and agent execution modes
- tools and MCP
- memory retrieval/storage surfaces
- traces, telemetry and benchmarks
- learning/routing policies
- scheduler and persistent operatives
- security scanning/guardrails

### OpenClaw adapter

Owns gateway and ecosystem integration:

- WebSocket Gateway and typed request/event protocol
- channel connections and pairing
- isolated multi-agent/session routing
- model-provider surfaces
- media I/O
- browser, exec, search, sandbox and automation tools
- skills/plugins/workflows
- desktop/mobile/headless nodes and device commands
- Control UI/TUI/CLI integration

### Omi adapter

Owns ambient perception and episodic capture:

- desktop/mobile/wearable capture
- BLE and device protocol
- live audio stream normalization
- STT provider routing/fallback
- diarization and speaker identity
- conversation finalization
- derived memories/action items
- app/webhook/MCP integration
- mobile/wearable SDK surfaces

Raw audio/video/screen frames should be treated as high-sensitivity transient data. Derived memory retention is separately policy-controlled.

### Clicky adapter / macOS embodiment

Owns immediate desktop companion behavior:

- menu-bar lifecycle
- push-to-talk
- screen capture across displays
- transcription provider abstraction
- vision prompt/context assembly
- streaming response UI
- TTS
- cursor overlay and target pointing
- element location detection
- transient overlay interaction state

Clicky's native interaction should become a client of the kernel rather than an independent memory/identity silo.

## 4. Memory architecture

Canonical memory types:

- **working** — short-lived context for the active task/session.
- **episodic** — attributable events/conversations/observations over time.
- **semantic** — consolidated facts/knowledge derived from evidence.
- **procedural** — skills, workflows and learned action procedures.
- **profile** — explicit user preferences/configuration.
- **evidence** — immutable pointers to artifacts/traces supporting claims.

Each memory record MUST include provenance, timestamps, confidence/derivation metadata, retention class and access scope.

OpenJarvis retrieval backends remain available as implementations. Omi memories become a source of episodic candidates, not a second independent truth model.

## 5. Cognition and model routing

OpenJarvis remains the primary cognitive runtime. Clever policy augments routing with:

- privacy class
- latency budget
- hardware availability
- energy/cost telemetry
- model capability
- offline state
- user/provider policy
- prior trace outcomes

Local-first is policy, not dogma: a cloud model may be selected when allowed and objectively required.

## 6. Action architecture

All side effects follow:

```text
intent → classify risk → authorize → execute → verify → persist result
```

Actions MUST have idempotency keys when retryable. No UI, channel, agent, plugin or retrieved document can bypass the policy broker.

## 7. Clever extensions beyond upstream parity

These are additive capabilities after or alongside parity work:

- Wake-word and hands-free session start.
- Barge-in / interruption while TTS is playing.
- Shared live goal graph across devices.
- Policy-controlled keyboard/mouse/computer control rather than pointing only.
- Proactive plans derived from persistent goals and monitored state.
- Context compression across long-running personal timelines.
- Cross-device handoff with conflict-free canonical state.
- Capability-aware planning: planner sees what each active device/runtime can actually do.
- Upstream drift bot that detects newly added capabilities and reopens parity work.

## 8. Integration strategy

### Stage A — federation
Pin upstream SHAs, inventory capabilities, run upstream tests and expose adapters. Do not rewrite.

### Stage B — canonicalization
Route identity/events/memory/policy through the kernel while preserving native runtime behavior.

### Stage C — convergence
Remove duplicated state only after behavioral parity tests prove canonical replacements.

### Stage D — optimization
Selective rewrites are allowed only with ADR + benchmark + parity evidence.

## 9. Reliability model

Every adapter publishes health and capability state. A capability may be:

`AVAILABLE | DEGRADED | UNAVAILABLE | BLOCKED_BY_POLICY | UNSUPPORTED`

False-green behavior is forbidden: lost audio, dropped events or failed tool calls cannot be reported as success.

## 10. Repository target layout

```text
Clever-Agent/
  kernel/
  contracts/
  adapters/
  upstream/
  apps/
  services/
  memory/
  policy/
  skills/
  tests/
    parity/
    integration/
    e2e/
    security/
    recovery/
  evidence/
  ledgers/
  scripts/
  docs/
```
