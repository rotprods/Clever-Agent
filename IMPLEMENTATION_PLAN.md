# IMPLEMENTATION PLAN — CLEVER-JARVIS-001

## Objective

Close CP01 with an evidence-backed capability denominator and compile a trustworthy CP02 contract frontier. This plan is executable; every phase has dependencies, outputs, gates and evidence requirements.

Machine-readable task order: `.agentic/context/NEXT_ACTIONS.json`. Human checklist: `TASKS.md`.

## Global execution rule

For every slice:

`BOOT_RECONCILE → OBSERVE → GRAPHIFY → MODEL → CROSS_LINK → PROJECT_20D → DECIDE → PLAN_COMPILE → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → AUTOPROMPT_REFLECT → COMMIT_RECONCILE`.

No phase advances from prose. No destructive convergence before `MIGRATION_ELIGIBLE`.

---

## Phase A — Integrity + W02 recovery (P0, immediate)

### A1. Context integrity gate

Deliverables:

- persist all decisions/risks referenced by ContextPack;
- regenerate ContextPack from ledgers;
- validate that every claim/risk/decision/evidence ID exists;
- validate `.agentic/CONFIG.yaml` frontier against execution state;
- validate machine task queue dependency graph;
- run context checks in Agentic Contract CI.

Exit:

`validate_agentic_state.py`, `validate_context_pack.py`, `validate_next_actions.py` and `build_context_pack.py --check` all pass from clean checkout.

### A2. Structural scanner performance correction

Replace `git ls-tree -l` with blobless tree metadata. Do not resolve blob sizes in CP01.

Exit:

- scanner remains deterministic;
- full tree still includes assets/unknown file types by path/object id;
- `size` is explicitly unknown where not available;
- unit test proves structural scan does not require blob size.

### A3. Final-head W02 evidence run

Run complete four-source structural inventory on the candidate HEAD.

Required evidence:

- exact pins reverified;
- 4 inventory JSONs;
- summary with tree entry counts/tree hashes;
- runtime below CI limit;
- artifact digest.

Exit W02 only after evidence persists and state mirrors agree.

---

## Phase B — W03 behavioral/public surface compiler

Goal: transform raw structural/source evidence into explicit executable/registered surfaces.

### B1. Surface schema

Define fields:

`surface_id, source_repo, source_commit, family, surface_kind, runtime_owner, source_paths, source_symbols/routes/keys, registration_evidence, protocol/interface, permissions, state_effects, lifecycle, failure_semantics, platform_constraints, evidence_strength, promotion_status`.

Initial promotion: `DISCOVERED_CANDIDATE`; explicit registration/route/protocol evidence can reach `BEHAVIOR_MAPPED`, never VERIFIED during W03 alone.

### B2. OpenJarvis extractor

Prioritize typed registries and actual registrations:

- ModelRegistry / EngineRegistry / AgentRegistry / MemoryRegistry / FactStoreRegistry;
- ToolRegistry / RouterPolicyRegistry / BenchmarkRegistry;
- Channel/Learning/Skill/Speech/TTS/Connector/Miner registries;
- CLI/API/MCP/scheduler/security surfaces;
- tests that exercise registered implementations.

### B3. OpenClaw extractor

Prioritize contribution/lifecycle surfaces:

- registerTool, registerChannel, provider families;
- gateway methods;
- services/commands/session extensions/actions;
- scheduler jobs/hooks/runtime lifecycle;
- node host commands/security audit/trusted tool policy;
- extension packages/plugins and their declared compatibility.

### B4. Omi extractor

Prioritize:

- FastAPI `include_router` topology + route definitions;
- listen receiver/contracts/registry/runtime;
- STT/TTS/diarization/speaker profiles;
- conversations/finalization/memories/action-items;
- desktop realtime/screen/frame surfaces;
- mobile/BLE/wearable/firmware/SDK boundaries;
- reconciliation/background workers.

### B5. Clicky extractor

Prioritize native Swift/worker behavior:

- PTT/audio capture/transcription;
- screen capture and multi-monitor context;
- TTS/stream response lifecycle;
- overlay/cursor/point localization;
- worker/proxy provider boundaries and secret handling.

### B6. W03 gauntlet

Compare extracted surfaces against:

- structural manifests/runtime boundaries;
- raw Graphify candidates;
- docs headings;
- tests;
- route/registry declarations.

Every unexplained orphan becomes a defect/risk, not a silent exclusion.

---

## Phase C — W04 capability denominator compiler

### C1. Capability schema + stable IDs

Canonical IDs must be deterministic, human-debuggable, collision-checked and insensitive to non-semantic formatting changes.

### C2. Behavior-equivalence rules

Deduplicate only when contract evidence supports equivalence. Preserve all contributing upstream provenance.

Not enough:

- same class/function name;
- same family label;
- same provider name;
- similar README description.

### C3. Denominator

Generate `ledgers/CAPABILITY_LEDGER.jsonl` and compute denominator from rows. No manual percentage.

At W04 close, capabilities may be `DISCOVERED/MAPPED`; Clever `VERIFIED` requires adapter behavioral parity later.

---

## Phase D — W05 upstream baseline compiler

Discover and classify build/test commands:

`RUNNABLE_HERE | PLATFORM_GATED | CREDENTIAL_GATED | HARDWARE_GATED | NETWORK_GATED | BROKEN_UPSTREAM | NOT_APPLICABLE`.

Run only safe bounded commands. Never turn NOT_RUN into PASS.

Persist command, toolchain/environment summary, status and artifact/log pointer.

---

## Phase E — W06 license + supply chain

- verify pinned licenses/notices;
- inventory lockfiles/manifests/workspaces;
- record attribution obligations;
- generate `licenses/UPSTREAM_NOTICES.md`;
- surface integration constraints as risks/decisions;
- prepare SBOM strategy for CP12.

---

## Phase F — W07 COS 20D completeness gauntlet

Build the capability dependency graph and apply 20D to high-value components/decisions, not raw nodes.

Minimum graph relations:

`requires, exposes, implemented_by, registered_via, persists_to, executes_on, permissioned_by, tested_by, owned_by, emits, consumes, recovers_via`.

Gauntlet:

- unrepresented runtime roots;
- registry keys with no surface;
- routes with no capability;
- tests with no mapped behavior;
- docs claims with no implementation evidence;
- state stores with no owner;
- side effects with no policy/rollback model;
- platform/device surfaces lost by generic normalization.

Exit only when every high-value orphan is resolved or explicitly open/blocking.

---

## Phase G — W08 CP01 close

Generate final report containing:

- exact source pins;
- structural counts;
- capability denominator;
- family/upstream distributions;
- evidence-strength distribution;
- baseline results;
- license/supply-chain findings;
- known limitations/risks;
- COS cross-repo pressure map;
- CP02 contract requirements derived from evidence.

Run all validators and gauntlets. Then and only then:

- CP01 → COMPLETE;
- CP02 → IN_PROGRESS;
- state/handoff/context/ledgers reconciled atomically.

---

## Phase H — CP02 entry compiler

Do not start until CP01 closes.

Compile versioned contract candidates for:

1. Identity / device / session / goal IDs.
2. Event envelope + provenance/correlation/causation.
3. Capability contribution registry combining OpenJarvis typing with OpenClaw lifecycle/rollback semantics.
4. Policy/action intent + authorization + idempotency + receipt.
5. Memory candidate/record/provenance/retention/access scope.
6. Runtime health/degradation/lifecycle.
7. Trace/evidence/evaluation contracts.

Rust kernel implementation follows contract tests; it does not precede them.

---

## Parallelization policy

Safe parallelism after W02:

- W03 per-upstream extractors may run in parallel once the shared surface schema is frozen.
- One agent owns shared schema/normalization files.
- Independent gauntlet reviews each upstream extractor.
- Security reviewer owns trust-boundary classifications.
- Release reconciler alone advances W03/W04 state after evidence.

Unsafe parallelism:

- two agents editing canonical state/context files;
- simultaneous capability ID scheme changes;
- concurrent state-migration design before behavior mapping.

## Milestone sequence

`M0 Context integrity → M1 W02 structural PASS → M2 W03 behavioral surface ledger → M3 W04 denominator → M4 baselines/license → M5 20D gauntlet → M6 CP01 report → M7 CP02 contracts`.

The current executable frontier is M0/M1, not CP02 implementation.
