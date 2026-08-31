# REGRESSION — CLEVER-JARVIS-001 — 2026-08-31

## Purpose

This regression reconstructs the actual engineering path from an almost-empty `Clever-Agent` repository to the current CP01 forensic/graph-control system. It separates verified facts from hypotheses, records mistakes and discarded assumptions, and defines the exact truth that future agents must inherit.

The source of truth for this document is Git + GitHub Actions evidence + canonical state/ledgers. Chat history is supporting context only.

## 1. Origin

The project began with one product-level intention: create a real JARVIS by unifying the useful capability union of four upstream systems without flattening them into a lowest-common-denominator rewrite:

- OpenJarvis — local cognition, engines, agents, memory, learning, traces, scheduling.
- OpenClaw — gateway, channels, nodes, plugins, tools, lifecycle and automation.
- Omi — ambient perception, mobile/wearable capture, transcription, diarization and episodic context.
- Clicky — macOS-native push-to-talk, screen perception, speech and visual pointing/overlay.

The key constraint became **capability preservation before consolidation**.

## 2. CP00 — canonical project bootstrap

The initial bootstrap established `CLEVER-JARVIS-001`, pinned exact upstream commits, defined the federated polyglot target architecture, security model, capability-parity contract, CP00–CP12 gates and durable state.

Important consequence: `100% parity` became a generated evidence ratio, not a claim based on README bullets.

## 3. Agentic development OS

Iteration 01 then established the repository as the durable operating system for development:

- `AGENTS.md` as canonical multi-agent execution contract;
- `/empezarproyecto` boot/recovery protocol;
- wave/claim/lease/handoff semantics;
- `STATE.md`, JSON state mirrors and append-only ledgers;
- Codex/Claude shims without vendor-specific constitutions;
- CI validation of canonical project state.

Operating law: **no wave, no production**.

## 4. W01 — exact upstream acquisition and first graph projection

W01 changed the source-acquisition architecture after observing upstream scale. Full worktree cloning was rejected. The accepted approach became:

`partial Git object store → immutable pin ref → optional source-only sparse projection`.

This preserved exact provenance while avoiding blind download/materialization of media, models and binary assets.

Verified evidence from GitHub Actions run `33402789051`:

1. all four exact upstream pins acquired;
2. exact commits and expected origins verified;
3. source-only projections materialized;
4. pins reverified after projection;
5. all four repositories Graphified;
6. COS hypergraph generated;
7. four-source provenance and non-destructive invariants passed;
8. forensic artifact uploaded with digest `sha256:f09dbec5fd39dbb97c56e8a3c986602a6b260adefb49f34a08aed791fc8fe6bc`.

The first full pass produced:

- 1,179,885 source-evidence nodes;
- 1,181,257 edges;
- 139 provisional COS component groups;
- 110 provisional cross-repository groups.

### Regression lesson

Those numbers are **not capability counts**. The evidence graph contains declarations, files, dependencies and heuristic candidates. Treating raw symbol density as behavior would create false equivalence and destructive deduplication.

Result: P0 raw evidence was separated from P1 behavioral surfaces and from the future capability denominator.

## 5. W02 — structural inventory compiler

W02 added a deterministic complete-Git-tree scanner using `git ls-tree` so structural coverage did not depend on the sparse worktree.

The first W02 CI run `33403318373` did not logically fail. It was cancelled by the 20-minute job timeout while executing `Compile structural inventories from complete Git trees`.

Verified timing:

- acquisition: ~17 seconds;
- pin verification: immediate;
- structural compile: ran ~19m55s and was cancelled;
- assertion/evidence upload were skipped.

### Root-cause regression

The scanner used `git ls-tree -l` against partial clones configured with `blob:none`. `-l` requests blob sizes; resolving sizes can defeat blobless acquisition by lazily resolving/fetching blob metadata/content. Blob size is not needed for CP01 capability discovery.

Corrective design:

- use tree metadata only: `mode`, `object type`, `object id`, `path`;
- keep blob `size = null/unknown` in structural CP01;
- do not trade provenance for expensive size collection;
- measure final-head runtime before W02 closure.

## 6. Graphify / COSGraph V2

The first Graphify/COS pass proved the need for four non-mutating planes:

- P0 `SOURCE_EVIDENCE` — exact source/test/docs/tree evidence;
- P1 `SEMANTIC_SURFACE` — compact candidate/behavioral surfaces;
- P2 `COS20D_DECISION` — provisional integration decisions with 20D analysis;
- P3 `AGENT_CONTEXT` — compact deterministic recovery view.

Derivation is one-way: `P0 → P1 → P2 → P3`. Higher planes cannot rewrite lower evidence.

COS-20L and COS-20D are orthogonal:

- 20L answers **where responsibility executes**;
- 20D answers **what must be understood/proven before changing it**.

The promotion ladder is:

`OBSERVED_SOURCE → DISCOVERED_CANDIDATE → BEHAVIOR_MAPPED → CONTRACT_MAPPED → TEST_MAPPED → VERIFIED → MIGRATION_ELIGIBLE`.

Only `MIGRATION_ELIGIBLE` may authorize destructive convergence or native-state removal.

## 7. Context-control regression

Commit `a9d6fa0...` installed the V2 context control plane and passed Graphify/COSGraph + Agentic Contract tests, but regression inspection found a continuity defect:

`CURRENT_CONTEXT.json` referenced `D-0006..D-0009` and `RISK-0004`, while the canonical ledgers only contained decisions through `D-0005` and risks through `RISK-0003`.

This is **memory ghosting**: a derived context view contained knowledge not persisted in the primary ledger.

Why existing CI missed it:

- Agentic Contract ran only `scripts/validate_agentic_state.py`;
- it did not execute `validate_context_pack.py` or `build_context_pack.py --check`;
- context consistency existed as code but not as an enforced merge gate.

Corrective rule:

> A derived ContextPack may never reference a claim/risk/decision/evidence ID that does not exist in canonical ledgers, and CI must fail if rebuilding the ContextPack changes bytes.

## 8. What is proven now

Proven:

- exact upstream pin strategy works;
- source projection can avoid binary/materialized upstream payloads;
- Graphify raw evidence generation works on all four sources;
- COS non-destructive overlay works;
- Graphify/COS unit/smoke gates are green on V2 head;
- federated polyglot architecture remains the correct default;
- OpenJarvis typed registries and OpenClaw contribution/lifecycle registries are complementary, not substitutes;
- Omi and Clicky overlap in perception but have different temporal/platform responsibilities;
- raw evidence must be separated from behavioral/capability truth.

Not yet proven:

- exhaustive W02 structural inventory on a completed final-head run;
- exhaustive registered/executable behavioral surfaces;
- the actual capability denominator;
- behavioral equivalence for cross-repo overlaps;
- baseline test/build compatibility for every upstream family;
- complete licensing/supply-chain integration obligations;
- final CP02 canonical contracts.

## 9. Current truth

- Global goal: `CLEVER-JARVIS-001` — IN_PROGRESS.
- Checkpoint: `CP01` — open.
- Iteration: `I01`.
- Complete: I01.0, W01.
- Active frontier: W02 structural inventory.
- Support subwave: `I01-W02-CTX` for COS V2/context integrity.
- Capability denominator: `NOT_GENERATED`.
- Clever parity: `0 VERIFIED`; upstream implementation existence is not Clever verification.
- No final Rust kernel contract may outrun CP01 evidence.

## 10. Regression conclusion

We have moved from “merge four assistants” to a safer and more scalable formulation:

**Preserve four upstream truths, compile their evidence, promote only real behavior, derive canonical contracts from proof, and converge implementation/state only after migration eligibility.**

The immediate mission is not more architecture prose. It is to finish W02 quickly and reproducibly, execute W03/W04 until the capability denominator exists, then close CP01 with adversarial completeness evidence.
