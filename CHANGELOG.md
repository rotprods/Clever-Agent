# CHANGELOG

All notable project-control and implementation changes are recorded here. Evidence and detailed run history live in append-only ledgers.

## 2026-08-31

### Regression + consciousness + executable planning control plane

- Added `docs/REGRESSION_2026-08-31.md` reconstructing CP00 → agentic OS → W01 → W02 → COS V2 with verified facts, discarded hypotheses and unresolved proof obligations.
- Added `docs/ACTA_DE_CONSCIENCIA.md` as the canonical human north-star / project-awareness handoff.
- Added `IMPLEMENTATION_PLAN.md`, `TASKS.md` and `.agentic/context/NEXT_ACTIONS.json` executable dependency graph.
- Added task-DAG validation for IDs, dependencies, cycles, frontier and executability.
- Persisted COS V2 decisions D-0006..D-0010 and context/performance risks RISK-0004..RISK-0005.
- Fixed ContextPack memory ghosting by deriving it from canonical ledgers and validating all referenced IDs.
- Added deterministic ContextPack + plan gates to Agentic Contract CI.
- Identified W02 timeout root cause: `git ls-tree -l` requested blob sizes against blobless partial clones.
- Changed structural inventory to complete Git tree metadata without blob-size resolution; unknown size is explicit and tested.
- Added final-head structural workflow trigger/contract checks; W02 remains open until a successful four-source run is persisted.

### COS Graph Engine V2 / 20D context control

- Added four graph planes: P0 source evidence, P1 semantic surfaces, P2 COS20D decisions, P3 agent context.
- Added COS-20D registry and promotion ladder through `MIGRATION_ELIGIBLE`.
- Added Graphify V2 compact semantic projection and COSGraph V2 provisional decision compiler.
- Added deterministic future-agent ContextPack and `/context`, `/graphify`, `/cos-graph-engineV2` command surfaces.
- Updated agent loop to graph-governed `BOOT_RECONCILE → ... → COMMIT_RECONCILE`.

### CP01 W01/W02 engineering

- Implemented exact-SHA partial object-store acquisition and immutable pin verification.
- Implemented source-only sparse projections.
- Ran full four-upstream Graphify/COS forensic workflow successfully; preserved artifact/digest evidence.
- Implemented complete-Git-tree structural inventory compiler; first full run timed out before evidence upload and therefore did not close W02.

### Agentic development bootstrap — Iteration 01

- Added mandatory `/empezarproyecto` boot/reconciliation command.
- Established wave-based execution: no material production mutation without a wave, claim, acceptance criteria and evidence.
- Added `STATE.md`, `HANDOFF.md`, `CHECKPOINTS.md` and durable ledgers.
- Added Iteration 01 forensic capability compiler plan and execution metaprompt.
- Added Claude/Codex instruction shims pointing to canonical `AGENTS.md`.
- Added repository validation script, PR template, CODEOWNERS and GitHub Actions state-contract validation.
- Extended global goal with durable multi-agent continuity and agent-death recovery acceptance criteria.

### Canonical project bootstrap

- Defined `CLEVER-JARVIS-001`.
- Pinned OpenJarvis, OpenClaw, Omi and Clicky snapshots.
- Established federated polyglot target architecture, parity policy and security model.
- Advanced global frontier to CP01 forensic upstream inventory.
