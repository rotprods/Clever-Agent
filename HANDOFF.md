# HANDOFF — Clever-Agent

## Handoff identity

- Project: `CLEVER-JARVIS-001`
- Iteration: `I01 — Forensic Capability Compiler`
- Completed waves: `I01-W00 — Agentic project bootstrap`, `I01-W01 — Pinned acquisition`
- Active frontier: `I01-W02 — Structural inventory`
- Next planned wave after W02: `I01-W03 — Public/behavioral surface extraction`
- Target branch after merge: `main`
- Global checkpoint: `CP01`

## What is now implemented

- Exact-SHA acquisition into `.cache/upstreams/<id>` as Git partial object stores.
- Immutable refs `refs/clever-agent/pinned/<id>`; no floating-main substitution.
- Pin verification of exact SHA + expected remote provenance.
- Source-only sparse projection for source/config inspection without pulling binary assets/models.
- `/graphify`: deterministic polyglot source/manifests → evidence graph.
- `/cosgraphengine`: COS-20L non-destructive integration hypergraph over Graphify outputs.
- W02 complete-tree structural scanner based on `git ls-tree`, independent of sparse materialization.
- Dedicated CI gates for compiler contracts, full four-upstream forensic scan and W02 structural inventory.

## W01 validation evidence

Full forensic workflow `CP01 Full Forensic Graph` run `33402789051`, job `99522924366`, completed `success` against `55f64b54e523122846a24504ea8842501bca9971`.

The run proved, in order:

1. all four exact upstream object stores acquired;
2. immutable pins verified;
3. source-only sparse projections materialized;
4. pins reverified after projection;
5. all four repositories Graphified;
6. COS hypergraph built;
7. four-source provenance + non-destructive invariants passed;
8. forensic artifact uploaded.

Artifact: `9762075538`, name `cp01-forensic-graph-55f64b54e523122846a24504ea8842501bca9971`, digest `sha256:f09dbec5fd39dbb97c56e8a3c986602a6b260adefb49f34a08aed791fc8fe6bc`.

Contract workflow `CP01 Graphify COSGraph` run `33402789018`: `success`. Agentic Contract run `33402788994`: `success`.

## Current forensic observations

The first full Graphify/COS pass generated 1,179,885 source evidence nodes and 1,181,257 source edges. It produced 139 provisional canonical component groups, of which 110 span multiple repositories.

These are **not 1,179,885 capabilities**. The raw graph intentionally includes files, declarations, dependencies and heuristic semantic candidates. The volume is dominated by TypeScript/OpenClaw declarations. W03/W04 must separate registered/executable behavioral surfaces from raw structural evidence before the denominator exists.

The provisional cross-repo topology supports the target direction but is not yet a migration authorization:

- orchestration, gateway/channel, inference, extension tooling and security show strong contract-normalization pressure;
- memory/persistence require convergent state/event semantics rather than competing truths;
- device, OS-native capture and much of embodiment should preserve upstream native implementations behind adapters.

## Current truth

CP01 remains open. `I01-W01` is complete. `I01-W02` implementation exists and is being validated. No upstream capability is yet marked Clever-Agent `VERIFIED`; the capability denominator is still `NOT_GENERATED`.

## Exact next action

1. Execute `/empezarproyecto` and validate state.
2. Inspect W02 workflow `33403318373` and its artifact if successful.
3. Persist W02 evidence/counts and mark `I01.2` complete only after the four complete Git-tree inventories pass.
4. Execute `I01-W03` with repository-specific surface extractors; prioritize registration/route/protocol evidence over lexical symbol names.
5. Preserve every source path/symbol/route as auditable evidence; do not deduplicate by description similarity.

## Known risks

- `RISK-0002`: dynamic/plugin/platform-gated surfaces can still be undercounted until the completeness gauntlet.
- `RISK-0003`: raw lexical/symbol classification can overcount and create false apparent overlaps if mistaken for behavioral parity. W03 explicit surfaces + W04 evidence-backed normalization are the mitigation.
- Structural JSONs may be large because they preserve the full Git tree; do not vendor upstream blobs to reduce them.

## Blockers

None known. W02 validation is an open gate, not a blocker.
