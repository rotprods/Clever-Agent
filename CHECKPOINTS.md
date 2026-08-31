# CHECKPOINTS — Human-readable execution map

`CHECKPOINT_REGISTRY.json` is the machine-readable authority. This file explains the same global gates and the current iteration's internal gates.

## Global lifecycle

| ID | Checkpoint | Status | Exit gate |
|---|---|---|---|
| CP00 | Canonical bootstrap | COMPLETE | Stable goal, architecture, security, upstream ledger, parity method and durable state exist. |
| CP01 | Forensic upstream inventory | IN_PROGRESS | All four pinned upstreams inventoried; exhaustive capability denominator, baseline test evidence and license inventory exist. |
| CP02 | Canonical contracts + Rust kernel scaffold | PENDING | Versioned contracts compile across target runtimes; core identity/event/capability/policy skeleton passes contract tests. |
| CP03 | OpenJarvis cognitive adapter | PENDING | OpenJarvis capability families parity-tested through canonical contracts. |
| CP04 | OpenClaw gateway adapter | PENDING | Gateway/channel/node/provider/tool/plugin/automation families parity-tested. |
| CP05 | Omi perception + episodic adapter | PENDING | Capture/STT/diarization/conversation/mobile/wearable/SDK families parity-tested. |
| CP06 | Clicky macOS embodiment | PENDING | PTT/screen/TTS/STT/overlay/pointing behavior parity-tested through shared identity/session contracts. |
| CP07 | Unified identity/events/memory | PENDING | Duplicate state converged without parity regression. |
| CP08 | Unified policy/action plane | PENDING | All side effects permissioned, idempotent, verified and audited; adversarial tests pass. |
| CP09 | Cross-device/multichannel continuity | PENDING | Same goal can hand off across supported devices/channels without state fragmentation. |
| CP10 | Learning + proactive autonomy | PENDING | Trace-driven improvements and proactive goal execution operate behind evaluation/security gates. |
| CP11 | 100% parity + upstream sync | PENDING | Generated parity report reaches 100% VERIFIED or approved waivers; drift detector works. |
| CP12 | Production hardening/release | PENDING | E2E, security, recovery, offline/degradation, performance, packaging, SBOM and release evidence pass. |

---

# Iteration 01 — Close CP01

Iteration 01 exists to create the **forensic capability compiler**. It does not build the final JARVIS kernel.

## I01.0 — Agentic repository bootstrap

**Status: COMPLETE**

Exit achieved: `/empezarproyecto`, wave/claim/handoff protocols, durable state/ledgers, tool shims, CI validator and iteration metaprompt exist.

## I01.1 — Reproducible upstream acquisition

**Status: COMPLETE** — evidence `EVID-0002` / W01 forensic run `33402789051`.

Exit achieved: all four exact SHAs reproducibly acquired/verified via partial object stores and immutable pin refs without vendoring upstream worktrees.

## I01.2 — Static repository inventory compiler

**Status: COMPLETE** — evidence `EVID-0005` / structural run `33429197669`.

Exit achieved:

- deterministic complete-Git-tree scanner enumerates paths, languages, package/workspace manifests, runtime boundaries, tests, CI/release, docs and license/notice surfaces;
- scanner is blobless and does not resolve blob sizes;
- all four exact sources successfully scanned;
- 50,681 total tree entries, 390 manifests, 17,651 tests and 615 runtime boundaries recorded.

## I01.3 — Behavioral/public-surface extraction

**Status: IN_PROGRESS / NEXT FRONTIER**

Exit requires source-backed inventory of:

- CLI commands;
- HTTP/WebSocket/API routes and protocols;
- registries/extension points;
- agents/models/engines/providers;
- tools/skills/plugins/channels/workflows;
- nodes/device commands/permissions/BLE/wearables;
- capture/STT/TTS/media/vision surfaces;
- memory/persistence/schedulers/background workers;
- security boundaries;
- tests/fixtures/benchmarks/release gates.

## I01.4 — Capability normalization + denominator compiler

**Status: PENDING**

Exit:

- `ledgers/CAPABILITY_LEDGER.jsonl` generated deterministically;
- canonical IDs/taxonomy and deduplication are tested;
- every in-scope row contains source repo/ref and source evidence;
- external ecosystems are modeled as extension capabilities, not discarded;
- parity denominator is computed from ledger state, never hand-entered.

## I01.5 — Upstream baseline test harness

**Status: PENDING**

Exit:

- runnable upstream test/build commands recorded by platform/runtime;
- available baseline tests executed hermetically where feasible;
- unavailable/platform-gated tests explicitly classified rather than marked passing;
- results stored under `evidence/cp01/baselines/`.

## I01.6 — Licensing, notices and supply-chain inventory

**Status: PENDING**

Exit:

- pinned licenses verified;
- required notices/attributions recorded;
- major package lock/manifests inventoried;
- integration constraints surfaced as decisions/risks.

## I01.7 — Capability graph + adversarial completeness gauntlet

**Status: PENDING**

Exit:

- capability dependency graph generated;
- coverage report detects evidence-less/unclassified surfaces;
- independent gauntlet searches for capabilities missed by scanner/normalizer;
- sampling against docs/tests/code does not find unexplained denominator gaps.

## I01.8 — CP01 close/reconciliation

**Status: PENDING**

Exit:

- all CP01 outputs reproducible;
- `STATE.md`, state JSON, capability/evidence/risk/decision ledgers reconciled;
- CP01 exit evidence linked;
- CP02 contract requirements generated from actual capability graph;
- CP01 status advanced only after validation/gauntlet passes.

---

## Checkpoint advancement rule

A subcheckpoint/checkpoint advances only when its exit condition is represented by persisted evidence. A future plan, generated documentation or an agent statement is not evidence of completion.
