# TASKS — CLEVER-JARVIS-001 executable backlog

Machine mirror: `.agentic/context/NEXT_ACTIONS.json`.

Statuses here are planning state; evidence/state ledgers remain authoritative for completion.

## P0 — Integrity / W02 closure — COMPLETE

- [x] **CTX-001 — Ledger/Context reconciliation.** Persist D-0006…D-0010 and RISK-0004…RISK-0005; regenerate ContextPack; reject orphan IDs.
- [x] **CTX-002 — Context CI gate.** Agentic Contract runs state validator + ContextPack validator + deterministic `--check` + task graph validator.
- [x] **CTX-003 — Planning graph validation.** Unique task IDs, dependency references, cycles, statuses and frontier validated.
- [x] **W02-001 — Blobless structural scan.** Removed `ls-tree -l`; size is explicitly unknown; full Git-tree coverage preserved.
- [x] **W02-002 — Final-head structural workflow.** Four exact upstream inventories passed in run `33429197669`.
- [x] **W02-003 — Persist W02 evidence.** Run/job/artifact digest and structural counts recorded as `EVID-0005`.
- [x] **W02-004 — Close I01.2.** State/handoff/context advance to W03; W02/CTX claims released.

## P1 — W03 surface extraction — ACTIVE FRONTIER

- [ ] **W03-001 — Behavioral surface schema.** Freeze source/protocol/owner/lifecycle/permission/state/failure/evidence fields.
- [ ] **W03-002 — OpenJarvis registered surfaces.** Typed registries, real registrations, CLI/API/MCP/scheduler/security/test mapping.
- [ ] **W03-003 — OpenClaw contribution surfaces.** Plugin registrars, gateway methods, channels/providers/tools/services/session/scheduler/hooks/security lifecycle.
- [ ] **W03-004 — Omi runtime surfaces.** FastAPI routers/routes, listen runtime/registry, STT/TTS, conversation/memory/reconciliation, desktop/mobile/wearable/device.
- [ ] **W03-005 — Clicky native surfaces.** Swift PTT/screen/TTS/overlay/pointing lifecycle + worker/proxy boundaries.
- [ ] **W03-006 — Evidence strength compiler.** Merge surface ledgers without behavior dedupe; classify definition/registration/route/protocol/test evidence and promotion status.
- [ ] **W03-007 — W03 completeness gauntlet.** Compare surfaces against tree/runtime roots/raw graph/docs/tests/registries.
- [ ] **W03-008 — Close W03.** Persist evidence and advance only if high-value orphans are explained.

## P1 — W04 capability denominator

- [ ] **W04-001 — Capability schema + stable IDs + equivalence rules.**
- [ ] **W04-002 — Generate `CAPABILITY_LEDGER.jsonl` and denominator.** No manual percentage; preserve provenance.
- [ ] **W04-003 — Denominator gauntlet.** Prove/repair undercount, overcount and false equivalence.

## P2 — W05 baseline tests

- [ ] **W05-001 — Baseline compiler.** Discover/classify safe build/test commands and persist exact outcomes; `NOT_RUN` is never PASS.

## P2 — W06 supply chain

- [ ] **W06-001 — License/NOTICE/lockfile/supply-chain compiler.** Cover all four exact sources and update risks/decisions.

## P2 — W07 graph gauntlet

- [ ] **W07-001 — Capability dependency graph + COS20D completeness gauntlet.** Detect orphan runtime roots, registrations, routes, tests, state, side effects and platform surfaces.

## P3 — W08 CP01 release gate

- [ ] **W08-001 — Generate CP01 report + CP02 requirements.** Counts must match machine ledgers.
- [ ] **W08-002 — Full validation + atomic CP01→CP02 transition.**

## P4 — CP02 entry — BLOCKED UNTIL W08

- [ ] **CP02-001 — Compile versioned identity/event/capability/policy/action/memory/health/trace contracts.** Round-trip tests precede Rust kernel scaffold.

## Immediate stop conditions

Do not generate the denominator before W03 completeness checks. Do not implement final CP02 kernel contracts before CP01 closes. Do not authorize migration from provisional COS decisions.
