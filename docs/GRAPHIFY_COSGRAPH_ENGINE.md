# `/graphify` + `/cosgraphengine` — CP01 semantic backend

Status: **implemented as a CP01 analysis substrate, not yet the final Clever-Agent runtime kernel**.

## Mission

Turn the four exact upstream snapshots in `UPSTREAM_LEDGER.yaml` into a reproducible, evidence-preserving software graph and then fuse those graphs into a non-destructive COS integration hypergraph.

The design explicitly separates two questions:

1. **What code/capability surface actually exists?** → `/graphify`.
2. **How should overlapping surfaces coexist inside Clever-Agent?** → `/cosgraphengine`.

Neither layer may infer that an upstream implementation can be deleted merely because another repository exposes a similarly named behavior.

## Upstream architecture observed at the pinned snapshots

| Upstream | Native role in the composite | Primary implementation stacks | Preserve natively |
| --- | --- | --- | --- |
| OpenJarvis | cognitive runtime, agents, inference, learning, local/cloud execution | Python; Rust/PyO3 native extension; Node bridges | inference engines, agent implementations, learning/eval primitives, hardware-aware execution |
| OpenClaw | gateway, sessions, channels, providers, nodes and plugin ecosystem | TypeScript/Node pnpm workspace, UI/packages/extensions | gateway/session semantics, plugin SDK, channel/provider/node adapters |
| Omi | ambient capture, memories, mobile/wearable/device runtime | Python/FastAPI backend; Flutter/Dart app; native/device/firmware surfaces | continuous capture pipeline, temporal memory behavior, BLE/wearable/device and mobile lifecycle code |
| Clicky | macOS desktop embodiment and low-latency push-to-talk UX | Swift/AppKit/SwiftUI/AVFoundation/ScreenCaptureKit; Cloudflare Worker | native permissions, overlay/cursor embodiment, global input, screen/audio integration |

The integration architecture is therefore intentionally **polyglot**. A premature single-language rewrite would erase mature OS/device behavior before parity evidence exists.

## `/graphify`

Entry point:

```bash
python -m scripts.graphify.cli .cache/upstreams/openjarvis \
  --repo-id openjarvis \
  --commit 72033b8ec288aa067ce4530ff9d96bf231e9c4e5 \
  --output graphs/upstreams/openjarvis.json
```

### Node classes

`repository`, `file`, `manifest`, `dependency`, `class`, `function`, `agent`, `provider`, `plugin`, `channel`, `persistence`, `device`, `media`, `security`, `tool`, `route`, `command`, `registry`, plus conservative fallback declarations.

Every source-derived node contains its pinned repo/commit provenance, path, line when available, language and content/surface metadata.

### Edge classes

The first slice emits `contains`, `declares` and `requires`. CP01 W03/W07 extends this vocabulary with `exposed_via`, `registers`, `implemented_by`, `persists_to`, `executes_on`, `permissioned_by` and `tested_by` once those relations are backed by deterministic extractors.

### Language strategy

Python uses the standard `ast` parser. TypeScript/JavaScript, Swift, Dart, Rust and C/C++ use conservative declaration/surface patterns in this first slice. Unsupported code is not silently promoted to capability evidence.

Manifests are parsed without executing upstream code. `package.json`, `pyproject.toml`, `Cargo.toml`, `requirements.txt`, `pubspec.yaml`, `go.mod` and workspace manifests become graph evidence.

## `/cosgraphengine`

Entry point:

```bash
python -m scripts.cosgraph.cli \
  --graph graphs/upstreams/openjarvis.json \
  --graph graphs/upstreams/openclaw.json \
  --graph graphs/upstreams/omi.json \
  --graph graphs/upstreams/clicky.json \
  --output graphs/cos_hypergraph.json
```

### COS-20L v0.1

The CP01 ontology has 20 layers:

`L0 Provider Boundary → L1 Capability → L2 Intent Routing → L3 Policy → L4 Claim/Lease → L5 Invocation → L6 Side Effect → L7 Receipt → L8 Event/Evidence → L9 Reducer/Outbox → L10 Durable State → L11 Projection/Index → L12 Session/Context → L13 Channel/Gateway → L14 Device Runtime → L15 Memory/Knowledge → L16 Observability/Economics → L17 Learning/Eval → L18 Governance/Security → L19 Embodiment/Experience`.

This is an **integration ontology** during CP01. CP02 may tighten contracts after the denominator is complete; it is not authorization to build the final kernel prematurely.

### Integration decisions

- `KEEP_NATIVE`: retain specialized OS/device/runtime implementation and wrap it.
- `ADAPT`: unique upstream surface receives a Clever-Agent adapter.
- `CANONICALIZE`: multiple implementations expose a common integration domain; define one contract while preserving implementations.
- `MERGE_STATE`: memory/persistence implementations participate in a canonical durable-state/event model instead of maintaining contradictory truth.
- `REWRITE_LATER`: reserved for a later evidence gate; the engine never emits it automatically in CP01.

### Hard invariant

`canonical_components` are overlays. `source_nodes` and `source_edges` remain intact. A similarity heuristic can nominate a shared contract; it cannot delete code.

## Target composite architecture

```text
[ Clicky macOS ]       [ Omi mobile/wearable ]      [ OpenClaw channels/nodes ]
       │                         │                              │
       └────────────── Provider / Capability Adapters ─────────┘
                                  │
                    ┌──────── Clever-Agent COS ────────┐
                    │ intent → policy → invocation     │
                    │ effect → receipt → event         │
                    │ state → projection → evidence   │
                    └──────────────────────────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
      OpenJarvis agents     canonical memory     OpenClaw gateway
      inference/learning    + event/state model  + plugin/channel SDK
```

## Acquisition contract

Before graph generation:

```bash
python -m scripts.upstream.sync_upstreams
python -m scripts.upstream.verify_pins
```

The cache is `.cache/upstreams/<id>` and remains uncommitted. Origin and HEAD are checked against `UPSTREAM_LEDGER.yaml`; no floating `main` substitution is accepted.

## Next compiler expansions

1. Language-aware import/call resolution and workspace ownership.
2. OpenClaw plugin/channel/provider registration extractors.
3. OpenJarvis registry/agent/engine/tool/memory extractors.
4. Omi FastAPI route, memory, plugin, BLE/device and firmware extractors.
5. Clicky Swift permission, ScreenCaptureKit/AVFoundation, overlay and worker route extractors.
6. Test-to-capability and permission-to-capability edges.
7. Completeness gauntlet comparing routes/registries/tests/docs against graph coverage.
8. Capability normalization from graph evidence into `CAPABILITY_LEDGER.jsonl`.

Until those gates close, graph nodes are `DISCOVERED` evidence, not Clever-Agent parity `VERIFIED` claims.
