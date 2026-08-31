# COS Graph Engine V2 — 20D graph-governed integration architecture

## 1. Purpose

COS Graph Engine V2 turns pinned source evidence into safe, reviewable integration work without flattening OpenJarvis, OpenClaw, Omi and Clicky into a guessed monolith.

V2 prevents raw symbol counts becoming fake capabilities, name similarity becoming destructive deduplication, decisions losing source/test provenance, and future agents resuming from stale chat.

It is a derived control plane, not a replacement for upstream runtimes and not a source-of-truth database.

---

## 2. Four graph planes

### P0 — Source / Evidence

Primary evidence from exact upstream commits: complete Git-tree inventory, source/config/tests/docs, `repository_graph` v1, baseline/license evidence. P0 is immutable from higher planes.

### P1 — Semantic Surface

Graphify V2 creates compact possible behavioral surfaces. W03 strengthens them with explicit registration, route, protocol, registry, plugin, provider and runtime ownership evidence. P1 starts at `DISCOVERED_CANDIDATE`, never `VERIFIED`.

### P2 — COS Decision

COS-20L classifies where runtime responsibility belongs. COS-20D evaluates what must be known before a safe integration decision advances. Decisions remain `PROVISIONAL` until promotion evidence exists.

### P3 — Agent Context

A compact deterministic recovery projection: frontier, pins, graph planes, hard invariants and IDs/pointers for claims, risks, decisions and evidence. It is deliberately small and derived.

Derivation is one-way: `P0 → P1 → P2 → P3`.

---

## 3. COS-20L vs COS-20D

These systems are orthogonal.

- **COS-20L** asks: where does responsibility execute?
- **COS-20D** asks: what must be understood before this integration/change is safe?

The exact D00–D19 registry is `.agentic/context/COS20D.json`: mission, provenance, topology, semantics, dependencies, ownership, interfaces, state, memory, intent, lifecycle, side effects, security, failure, observability/economics, test/parity, platform/device, embodiment, supply-chain and temporal drift.

20D applies to components, decisions, waves and ContextPacks — not every raw source node.

---

## 4. Promotion ladder

`OBSERVED_SOURCE → DISCOVERED_CANDIDATE → BEHAVIOR_MAPPED → CONTRACT_MAPPED → TEST_MAPPED → VERIFIED → MIGRATION_ELIGIBLE`

A symbol can be observed without being a feature. A registered route can be behavior-mapped without being parity-verified. A parity-verified behavior can remain non-migratable if state/security/recovery semantics differ.

Only `MIGRATION_ELIGIBLE` can support removal/replacement of native behavior or state.

---

## 5. Integration decisions

V2 retains:

- `KEEP_NATIVE` — preserve specialized implementation behind canonical contract/adapter.
- `ADAPT` — expose native behavior through a canonical boundary.
- `CANONICALIZE` — converge interface/contract semantics, not implementation by default.
- `MERGE_STATE` — converge state/event semantics only after migration proof.
- `REWRITE_LATER` — replacement may be useful after parity/benchmark evidence.

Every V2 decision contains source component/repositories/nodes, proposed decision, `PROVISIONAL` status, `UNVERIFIED` confidence, promotion status, relevant 20D dimensions, required promotions, `rewrite_allowed=false` and `migration_authorized=false`.

The decision graph cannot authorize its own rewrite.

---

## 6. Canonical loop

`BOOT_RECONCILE → OBSERVE → GRAPHIFY → MODEL → CROSS_LINK → PROJECT_20D → DECIDE → PLAN_COMPILE → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → AUTOPROMPT_REFLECT → COMMIT_RECONCILE`

Each cycle either advances with evidence, blocks with evidence, rolls back with evidence or proves no change.

---

## 7. Upstream-specific convergence

### OpenJarvis

Preserve typed cognitive abstractions: engines, agents, memory/retrieval, tools, routing/learning, traces, schedulers, guardrails and typed registries. It is a strong source for cognitive capability typing.

### OpenClaw

Preserve contribution/lifecycle semantics: plugin discovery/registration, tools/channels/providers, gateway methods, services, commands, session extensions, scheduler jobs, hooks, security guards and rollback of plugin side effects. It is a strong source for ownership/lifecycle/rollback semantics.

### Omi

Preserve ambient capture, mobile/wearable/device integrations, transcription, speaker identity, conversation finalization, memory extraction and extensive backend routes. Omi is a major source for episodic/perception/state recovery semantics; native capture/device behavior remains adapter-owned until parity/platform tests prove otherwise.

### Clicky

Preserve macOS-native embodiment: PTT, screen capture, overlay/cursor, TTS/transcription and desktop lifecycle. Do not rewrite platform-native UX because another repo has a similarly named surface.

---

## 8. Canonical registry direction

The future Clever registry should combine OpenJarvis typed primitives with OpenClaw contribution/lifecycle/rollback semantics.

A canonical contribution should eventually model identity/family, runtime/plugin/device owner, versioned interface, lifecycle, permissions/policy, state and side effects/idempotency, health/degradation, rollback/recovery, provenance and test/evidence mapping.

This is a direction to be proven by CP01/CP02, not permission to implement final kernel APIs during CP01.

---

## 9. State convergence gate

Before any `MERGE_STATE` is migratable, prove canonical owner/schema/event semantics; all native reads/writes; conflict/concurrency; retry/idempotency; backfill/migration; cutover; failure/recovery; security/retention/access; parity tests; and rollback.

Until then native stores remain authoritative inside their adapters.

---

## 10. Context engineering

`.agentic/context/CURRENT_CONTEXT.json` lets a fresh agent recover without replaying chat or every ledger line. It contains IDs/pointers and hard invariants; full chronology remains in append-only ledgers.

Future agents validate canonical state, validate/rebuild ContextPack, reconcile claims/Git, load COS-20D and continue the persisted frontier.

---

## 11. Scale rules

The real forensic graph exceeds one million source evidence nodes. Therefore:

- raw graph stays lossless/mechanically generated;
- semantic projections are compact and purpose-specific;
- 20D applies to decisions/components, not all source nodes;
- large artifacts may remain external CI evidence;
- checked-in state stores summaries/digests/pointers instead of duplicate huge graphs.

---

## 12. Health criteria

V2 is healthy when exact pins resolve; state/config/context agree; graph derivation is deterministic; promoted behaviors retain provenance; provisional decisions cannot authorize migration; gauntlet detects orphan high-value surfaces; context drift fails CI; and a fresh agent can identify exact frontier/first action from repository truth alone.
