# IMPLEMENTATION PLAN — CLEVER-JARVIS-001

## Current position

- CP01: IN_PROGRESS.
- I01.0 / I01.1 / I01.2: COMPLETE.
- Current wave: `I01-W03 — Public/behavioral surface extraction`.
- First executable task: `W03-001`.
- Capability denominator: NOT_GENERATED.

Machine task authority: `.agentic/context/NEXT_ACTIONS.json`. Human checklist: `TASKS.md`.

## Execution loop

`BOOT_RECONCILE → OBSERVE → GRAPHIFY → MODEL → CROSS_LINK → PROJECT_20D → DECIDE → PLAN_COMPILE → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → AUTOPROMPT_REFLECT → COMMIT_RECONCILE`.

No destructive convergence before `MIGRATION_ELIGIBLE`.

---

## M0 — Context/control integrity — COMPLETE

Proven:

- state/context/task DAG cross-validation;
- ledger-backed ContextPack with orphan-ID rejection;
- deterministic rebuild CI;
- 20D registry and graph-plane invariants;
- GOAL/EXECUTION/iteration/CONFIG/frontier reconciliation.

Evidence: `EVID-0004`.

## M1 — W02 structural census — COMPLETE

Proven:

- complete blobless Git-tree scan of all four exact upstreams;
- 50,681 entries / 390 manifests / 17,651 tests / 615 runtime boundaries;
- no blob-size resolution;
- final structural workflow success and artifact digest.

Evidence: `EVID-0005`.

---

## M2 — W03 behavioral surface compiler — ACTIVE

### W03-001 — Freeze the schema

Define `behavioral_surface.schema.json` with at least:

`surface_id, source_repo, source_commit, family, surface_kind, runtime_owner, source_paths, source_symbols/routes/keys, registration_evidence, protocol/interface, permissions, state_effects, lifecycle, failure_semantics, platform_constraints, evidence_strength, promotion_status`.

Evidence strength should distinguish at minimum:

`LEXICAL_HINT < DEFINITION < REGISTRATION < ROUTE_OR_PROTOCOL < BEHAVIOR_TEST`.

W03 may promote explicit surfaces to `BEHAVIOR_MAPPED`; it does not create Clever `VERIFIED` capabilities.

### W03-002 — OpenJarvis lane

Extract typed registries, actual registrations, CLI/API/MCP, scheduler, security and tests. Preserve registry key → implementation → test/source edges.

### W03-003 — OpenClaw lane

Extract plugin contribution/lifecycle surfaces: tools, channels, provider families, gateway methods, services, commands, session actions/extensions, scheduler jobs/hooks, node host commands, security/trusted-tool/lifecycle/rollback.

### W03-004 — Omi lane

Extract FastAPI include-router topology/routes, listen contracts/runtime/registry, STT/TTS/diarization/speaker identity, conversations/finalization/memory/action items, reconciliation jobs, desktop/mobile/BLE/wearable/firmware/SDK boundaries.

### W03-005 — Clicky lane

Extract Swift PTT/audio/screen/multi-monitor/TTS/streaming/overlay/pointing lifecycle plus worker/proxy/provider/secret boundaries.

### W03-006 — Unified surface ledger

Merge source ledgers **without behavior deduplication**. Assign evidence strength and promotion status; preserve all provenance.

### W03-007 — Completeness gauntlet

Cross-check against:

- W02 structural roots/manifests;
- P0 raw Graphify candidates;
- registry keys/routes/commands;
- docs claims;
- tests/fixtures;
- state stores/background workers/platform roots.

Every unexplained high-value orphan becomes a defect/risk/blocker.

### W03-008 — Close W03

Persist evidence and advance only after the high-value orphan gate is satisfied.

Parallelism: after W03-001 schema is frozen, W03-002…005 can run in separate worktrees/agents because their write surfaces are disjoint. One owner controls the shared schema/merge code.

---

## M3 — W04 capability denominator

1. Capability schema and stable deterministic IDs.
2. Contract-equivalence rules; never dedupe from names/descriptions alone.
3. Generate `CAPABILITY_LEDGER.jsonl` with all source provenance.
4. Compute denominator automatically.
5. Adversarial undercount/overcount/false-equivalence gauntlet.

At W04 close the denominator exists, but Clever behavior is not globally VERIFIED until adapter parity tests later.

---

## M4 — W05 baselines + W06 supply chain

Run in parallel after W04 gauntlet:

- W05 discovers/classifies safe upstream build/test commands (`RUNNABLE_HERE`, `PLATFORM_GATED`, `CREDENTIAL_GATED`, `HARDWARE_GATED`, `NETWORK_GATED`, `BROKEN_UPSTREAM`, `NOT_APPLICABLE`) and persists exact results.
- W06 verifies licenses/notices/lockfiles/workspaces and produces upstream attribution/supply-chain evidence.

Never map NOT_RUN to PASS.

---

## M5 — W07 COS20D completeness gauntlet

Build the capability dependency graph with at least:

`requires, exposes, implemented_by, registered_via, persists_to, executes_on, permissioned_by, tested_by, owned_by, emits, consumes, recovers_via`.

Apply COS20D to high-value components/decisions. Detect orphan runtime roots, registrations, routes, tests, state stores, side effects and platform/device behaviors.

---

## M6 — W08 CP01 release gate

Generate:

- `reports/CP01_CAPABILITY_REPORT.md`;
- evidence-derived `reports/CP02_CONTRACT_REQUIREMENTS.md`;
- final pin/count/denominator/evidence/baseline/license/risk/COS pressure matrix.

Only after the complete validation suite passes:

`CP01 COMPLETE → CP02 IN_PROGRESS`.

---

## M7 — CP02 contracts — BLOCKED UNTIL M6

Compile versioned contracts for:

1. identity/device/session/goal;
2. event envelope + provenance/correlation/causation;
3. capability contribution registry (OpenJarvis typed primitives × OpenClaw lifecycle/rollback);
4. policy/action/authorization/idempotency/receipt;
5. memory provenance/retention/access;
6. runtime health/degradation/lifecycle;
7. trace/evidence/evaluation.

Generate Rust/Python/TypeScript/Swift bindings and round-trip/version-skew tests before the Rust kernel scaffold.

## Stop conditions

- No W04 denominator before W03 completeness.
- No CP02 kernel before W08 closes CP01.
- No `MERGE_STATE`/rewrite execution from provisional COS decisions.
- No capability exclusion simply to improve the parity percentage.
