# Graph Engineering Protocol — Clever-Agent

## 1. Objective

Build a provenance-preserving graph for exhaustive inventory, parity accounting, architecture decisions and future-agent recovery without confusing structural similarity with behavioral equivalence.

## 2. Node classes

Model repository/package/manifest/file/symbol; routes/commands/RPC/MCP; registries/extensions/plugins/tools/channels; providers/engines/agents/workflows/schedulers/services; persistence/memory/media/device/security; canonical contracts; tests/evals; state/event schemas; risks/decisions/waves/claims; evidence; COS facets/20D decisions.

Do not create a new node type merely because a parser emitted a lexical pattern.

## 3. Edge vocabulary

Structural: `contains | declares | imports | requires | owns | generated_from`

Runtime: `registers | exposes | invokes | emits | consumes | schedules | executes_on`

State: `reads | writes | persists_to | retrieves_from | derived_from | migrates_to`

Governance: `permissioned_by | policy_gated_by | sandboxed_by | claims | supersedes`

Evidence: `observed_at | implemented_by | tested_by | evidenced_by | contradicts`

Decision: `classified_as | proposes_integration_for | canonicalizes_with | adapts_to | keeps_native | blocks_migration`

Every derived edge carries attributable evidence where possible.

## 4. Identity and determinism

Stable source IDs derive from immutable semantic identity plus repository/commit/path/symbol evidence. Downstream classifications never rewrite source IDs. Sort deterministic outputs; keep timestamps/runner paths out of semantic hashes; fail closed on collisions.

## 5. Evidence strength

- `E0_LEXICAL` — name/text match.
- `E1_STRUCTURE` — source/manifests/tree location.
- `E2_REGISTRATION_OR_PROTOCOL` — explicit route/registry/protocol/extension declaration.
- `E3_RUNTIME_OR_TEST` — runtime wiring or executable test proves behavior.
- `E4_CONTRACT_EQUIVALENCE` — behavioral/state/failure/security equivalence proven.
- `E5_PARITY_VERIFIED` — Clever-Agent parity mapping + tests/evidence complete.

E0/E1 are discovery signals; they normally cannot create a capability row alone.

## 6. Hyperedges and multi-source decisions

Use hyperedges for decisions involving several implementations, stores, protocols or evidence items. Pairwise edges must not imply equivalence when the actual contract is n-ary.

## 7. Temporal graph

Every source observation is versioned by pinned commit. Upstream drift creates new observations and explicit drift relationships. Historical evidence is append-only.

## 8. Large-graph strategy

Keep lossless raw evidence, compact semantic projection, compact decision/hypergraph and tiny ContextPack. Do not force every query through a million-node JSON document; generate indexes/projections while preserving raw backreferences.

## 9. Wave graph contract

Each wave identifies:

```text
graph_inputs
new_or_changed_nodes
new_or_changed_edges
promotion_delta
decision_delta
20D_dimensions_touched
evidence_delta
unresolved_orphans
```

Architecture work without an identifiable graph delta is under-modeled.

## 10. Graph gauntlet

Search for routes/registries/plugin contracts missing from P1; tests without behavior; E0/E1-only candidates; decisions without provenance; name-only grouping; `MERGE_STATE` without read/write/failure/migration; security without policy edges; native device/UX marked canonicalizable; orphan apps/services/manifests; stale pins or ContextPack.

## 11. Autoprompting queries

After every material cycle ask:

1. Which high-value source surfaces remain unrepresented?
2. Which candidates lack E2+ evidence?
3. Which cross-repo families have multiple owners and no canonical contract?
4. Which decisions touch open risks?
5. Which stateful components lack idempotency/recovery mapping?
6. Which capabilities lack tests?
7. Which platform-native behaviors should remain native?
8. Which decisions are blocked from promotion and by what evidence?
9. Which upstream drift invalidates current assumptions?
10. What smallest non-conflicting wave closes the highest-value evidence gap?

Autoprompting proposes work; it never self-approves a checkpoint or migration.
