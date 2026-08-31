# TASKS — CLEVER-JARVIS-001 executable backlog

Machine mirror: `.agentic/context/NEXT_ACTIONS.json`.

Statuses here are planning state; evidence/state ledgers remain authoritative for completion.

## P0 — Integrity / W02 closure

- [ ] **CTX-001 — Ledger/Context reconciliation.** Persist D-0006…D-0010 and RISK-0004…RISK-0005; regenerate ContextPack; reject orphan IDs.
- [ ] **CTX-002 — Context CI gate.** Agentic Contract must run state validator + ContextPack validator + deterministic `--check` + task graph validator.
- [ ] **CTX-003 — Planning graph validation.** Validate unique task IDs, dependency references, cycles, statuses, and first executable frontier.
- [ ] **W02-001 — Blobless structural scan.** Remove `ls-tree -l`; keep size unknown; prove full path/object coverage.
- [ ] **W02-002 — Final-head structural workflow.** Re-run 4 upstream inventories on candidate HEAD with exact pins.
- [ ] **W02-003 — Persist W02 evidence.** Record run/job/artifact digest and structural counts.
- [ ] **W02-004 — Close I01.2.** Release W02 claim, update STATE/JSON/HANDOFF/ContextPack and advance to W03.

## P1 — W03 surface extraction

- [ ] **W03-001 — Behavioral surface schema.** Freeze source/protocol/owner/lifecycle/permission/state/failure/evidence fields.
- [ ] **W03-002 — OpenJarvis registered surfaces.** Typed registries, real registrations, CLI/API/MCP/scheduler/security/test mapping.
- [ ] **W03-003 — OpenClaw contribution surfaces.** Plugin registrars, gateway methods, channels/providers/tools/services/session/scheduler/hooks/security lifecycle.
- [ ] **W03-004 — Omi runtime surfaces.** FastAPI routers/routes, listen runtime/registry, STT/TTS, conversation/memory/reconciliation, desktop/mobile/wearable/device.
- [ ] **W03-005 — Clicky native surfaces.** Swift PTT/screen/TTS/overlay/pointing lifecycle + worker/proxy boundaries.
- [ ] **W03-006 — Evidence strength compiler.** Classify lexical/definition/registration/route/protocol/test evidence and promotion status.
- [ ] **W03-007 — Surface merge without dedupe.** Create unified surface ledger preserving every source provenance.
- [ ] **W03-008 — W03 completeness gauntlet.** Compare surfaces against tree/runtime roots/raw graph/docs/tests/registries.
- [ ] **W03-009 — Close W03.** Persist evidence and advance only if high-value orphans are explained.

## P1 — W04 capability denominator

- [ ] **W04-001 — Capability schema.** Define canonical behavior contract, provenance and parity status.
- [ ] **W04-002 — Stable capability IDs.** Deterministic, collision-tested IDs.
- [ ] **W04-003 — Equivalence engine.** Require contract evidence before dedupe; preserve multi-upstream provenance.
- [ ] **W04-004 — Generate `CAPABILITY_LEDGER.jsonl`.** No manual capability rows outside governed exceptions.
- [ ] **W04-005 — Compute denominator/report.** Generated counts by family/upstream/status/evidence.
- [ ] **W04-006 — Denominator gauntlet.** Try to prove undercount/overcount from source/tests/docs.
- [ ] **W04-007 — Close W04.** Mark denominator GENERATED; do not mark Clever parity VERIFIED.

## P2 — W05 baseline tests

- [ ] **W05-001 — Build/test command discovery.** Extract commands/toolchains from manifests/CI/docs.
- [ ] **W05-002 — Gate classification.** RUNNABLE/PLATFORM/CREDENTIAL/HARDWARE/NETWORK/BROKEN/NA.
- [ ] **W05-003 — Safe baseline execution.** Sandboxed/bounded where feasible; persist exact outcomes.
- [ ] **W05-004 — Baseline matrix report.** Capability/test links and blockers.

## P2 — W06 supply chain

- [ ] **W06-001 — License/NOTICE verification.** Exact pinned-source evidence.
- [ ] **W06-002 — Lockfile/workspace inventory.** Major dependency manifests and package boundaries.
- [ ] **W06-003 — `UPSTREAM_NOTICES.md`.** Attribution and observable integration obligations.
- [ ] **W06-004 — Supply-chain risks.** Update risk/decision ledgers.

## P2 — W07 graph gauntlet

- [ ] **W07-001 — Capability dependency graph.** requires/exposes/implemented_by/registered_via/persists_to/executes_on/permissioned_by/tested_by/owned_by/emits/consumes/recovers_via.
- [ ] **W07-002 — COS20D projection.** Apply 20D to high-value components/decisions.
- [ ] **W07-003 — Orphan detector.** Runtime roots/registries/routes/tests/state/side effects/platform surfaces.
- [ ] **W07-004 — Independent adversarial sampling.** Manual/automated source sampling against generated ledger.
- [ ] **W07-005 — Resolve/block every critical orphan.** No silent exclusions.

## P3 — W08 CP01 release gate

- [ ] **W08-001 — Generate CP01 report.** Pins, counts, denominator, evidence, baselines, licenses, risks, graph findings.
- [ ] **W08-002 — Compile CP02 requirements.** Derive contracts from graph/evidence.
- [ ] **W08-003 — Full CP01 validation suite.** State/context/task/schema/graph/gauntlet/recovery checks.
- [ ] **W08-004 — Reconcile and close CP01.** Update checkpoint registry/state/context/handoff/ledgers atomically.

## P4 — CP02 entry (blocked until W08)

- [ ] **CP02-001 — Identity/session/device/goal contracts.**
- [ ] **CP02-002 — Canonical event envelope.** Provenance, correlation, causation, classification.
- [ ] **CP02-003 — Capability contribution contract.** OpenJarvis typed primitives × OpenClaw lifecycle/rollback.
- [ ] **CP02-004 — Policy/action/receipt contract.** Authorization, idempotency, verification.
- [ ] **CP02-005 — Memory contract.** Working/episodic/semantic/procedural/profile/evidence + retention/access/provenance.
- [ ] **CP02-006 — Health/lifecycle contract.** AVAILABLE/DEGRADED/UNAVAILABLE/BLOCKED/UNSUPPORTED.
- [ ] **CP02-007 — Cross-runtime codegen + round-trip tests.** Rust/Python/TypeScript/Swift.
- [ ] **CP02-008 — Rust kernel scaffold.** Only after contract tests pass.

## Immediate stop conditions

Do not start W03 if W02 does not have a successful evidence artifact. Do not generate the denominator before W03 completeness checks. Do not implement final CP02 kernel contracts before CP01 closes. Do not authorize migration from provisional COS decisions.
