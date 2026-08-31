# REGRESSION — CLEVER-JARVIS-001 — 2026-08-31

## Purpose

This is the canonical engineering regression from the original “merge four agent repos” idea to the current evidence-governed JARVIS integration system. Facts are grounded in Git/state/GitHub Actions; discarded hypotheses are recorded when they materially changed the design.

## 1. Origin: an intuitive union problem

The original mission was to unify the useful capability union of OpenJarvis, OpenClaw, Omi and Clicky inside `rotprods/Clever-Agent`.

The four upstreams are complementary:

- OpenJarvis: cognition, inference engines, typed agents/tools/memory/learning/scheduling.
- OpenClaw: gateway, channels, nodes, plugin contributions, lifecycle, tools and automation.
- Omi: ambient audio/screen context, transcription/diarization, conversations/memory, mobile/wearable/device runtime.
- Clicky: macOS-native PTT, screen perception, streaming response/TTS and pointing/overlay embodiment.

The first architectural correction was to define **capability preservation before consolidation**. “100%” must mean a generated evidence-backed denominator, not feature bullets or code volume.

## 2. CP00: canonical project contract

CP00 established `CLEVER-JARVIS-001`, exact upstream pins, federated polyglot architecture, security model, parity methodology, CP00–CP12 checkpoints and durable project state.

This prevented an early monolithic rewrite. Rust became the target for new canonical kernel/control surfaces, not a mandate to replace mature Python/TypeScript/Swift/Flutter/Zephyr implementations.

## 3. Agentic operating system

Iteration 01 made the repository—not chat—the development operating system:

- `AGENTS.md` is the execution authority;
- `/empezarproyecto` restores durable state;
- material work belongs to waves/claims;
- state/decisions/risks/evidence are persisted;
- Claude/Codex/ChatGPT consume one constitution rather than vendor-specific forks;
- CI validates continuity.

Rule: **no wave, no production**.

## 4. W01: exact-SHA acquisition and first graph

A full-checkout approach was rejected after upstream scale inspection. W01 adopted:

`partial Git object store → immutable pinned ref → source-only sparse projection when content is needed`.

GitHub Actions run `33402789051` proved all four exact refs, provenance, sparse projection, four Graphify outputs and non-destructive COS graph construction.

Raw output:

- 1,179,885 evidence nodes;
- 1,181,257 edges;
- 139 provisional component groups;
- 110 provisional cross-repository groups.

### Lesson

Those are evidence nodes, **not capabilities**. A million symbols do not imply a million product behaviors. Lexical similarity cannot authorize deduplication.

This led to explicit separation between raw evidence, behavioral surfaces, canonical capabilities and migration decisions.

## 5. W02: structural inventory regression and repair

W02 introduced complete-Git-tree structural inventory independent of sparse worktree materialization.

The first full run `33403318373` did not prove a logic failure. Acquisition and pin verification passed; the structural compile ran ~19m55s and was cancelled by the job's 20-minute timeout.

Root cause: `git ls-tree -l` requested blob sizes against `blob:none` partial clones. That contradicted W01 by potentially forcing lazy blob resolution.

Correction:

- use `git ls-tree -r -z` tree metadata only;
- retain mode/type/object-id/path;
- size is explicitly `null/unknown` in CP01;
- unit tests enforce blobless semantics.

Final run `33429197669`, job `99610115447`, passed every step and uploaded artifact `9771912520`, digest `sha256:71dc9e002a8874cffdb63440c9fdd0d4042ceb623ec7927b214e6a4ae0a94221`.

Final structural census:

| Upstream | Tree entries | Manifests | Tests | Runtime boundaries |
|---|---:|---:|---:|---:|
| OpenClaw | 35,757 | 213 | 13,613 | 362 |
| Omi | 12,731 | 141 | 3,314 | 198 |
| OpenJarvis | 2,108 | 32 | 724 | 51 |
| Clicky | 85 | 4 | 0 | 4 |
| **Total** | **50,681** | **390** | **17,651** | **615** |

W02 is therefore COMPLETE.

## 6. COS Graph Engine V2 / 20D

The graph architecture evolved into four immutable-direction planes:

`P0 SOURCE_EVIDENCE → P1 SEMANTIC_SURFACE → P2 COS20D_DECISION → P3 AGENT_CONTEXT`.

Higher planes derive from lower planes and never rewrite source evidence.

Two orthogonal coordinate systems are now explicit:

- **COS-20L**: where runtime responsibility executes.
- **COS-20D**: what must be understood/proven before integration/change.

20D is projected onto canonical components/decisions/waves/ContextPacks—not every raw node.

Promotion ladder:

`OBSERVED_SOURCE → DISCOVERED_CANDIDATE → BEHAVIOR_MAPPED → CONTRACT_MAPPED → TEST_MAPPED → VERIFIED → MIGRATION_ELIGIBLE`.

Only `MIGRATION_ELIGIBLE` may authorize destructive convergence.

## 7. Context-layer regression: memory ghosting

Regression inspection found `CURRENT_CONTEXT.json` referencing decisions/risks that did not yet exist in canonical ledgers. That was a real continuity defect: a derived recovery view had become more knowledgeable than the primary truth.

Correction:

- decisions D-0006…D-0010 and risks RISK-0004/RISK-0005 persisted;
- ContextPack derives from state + ledgers;
- every referenced decision/risk/claim/evidence ID is cross-validated;
- `NEXT_ACTIONS.json` is an acyclic executable dependency graph;
- deterministic ContextPack rebuild is CI-enforced;
- `GOAL_STATE.frontier`, execution state, iteration state, CONFIG and ContextPack are now cross-checked.

Agentic Contract runs on `8dded838...` passed, proving state/context/task-DAG integrity after the repair.

## 8. What is proven now

Proven:

- exact upstream snapshot acquisition/provenance;
- non-destructive source projection;
- raw Graphify/COS operation across all four upstreams;
- complete structural census of all four Git trees;
- COS V2 graph-plane/20D/context contracts;
- ledger-backed future-agent ContextPack;
- executable task DAG and continuity CI.

Not yet proven:

- exhaustive registered/executable behavioral surfaces;
- actual capability denominator;
- behavioral equivalence for apparent cross-repo overlaps;
- upstream baseline compatibility matrix;
- complete license/supply-chain integration obligations;
- final CP02 canonical contracts.

## 9. Current truth

- Goal: `CLEVER-JARVIS-001` — IN_PROGRESS.
- Global checkpoint: `CP01` — IN_PROGRESS.
- Completed iteration gates: I01.0, I01.1, I01.2.
- Active subcheckpoint/wave: `I01.3 / I01-W03`.
- First executable task: `W03-001 — Behavioral surface schema`.
- Capability denominator: `NOT_GENERATED`.
- Clever parity: 0 VERIFIED; upstream implementation existence is not Clever parity evidence.

## 10. Regression conclusion

The project has moved from **“combine four repositories”** to a safer compiler model:

> Preserve source truth → extract real behavior → normalize contracts with provenance → test equivalence → integrate behind canonical contracts → migrate implementation/state only after proof.

The next phase is not more broad architecture. It is W03: explicit registered/executable surface extraction from each upstream.
