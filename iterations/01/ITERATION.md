# Iteration 01 — Forensic Capability Compiler

## Identity

- Iteration: `I01`
- Goal: `CLEVER-JARVIS-001`
- Global checkpoint: `CP01`
- Type: foundation / forensic compiler / evidence system
- Kernel implementation allowed: **no final kernel contracts before denominator evidence**

## Objective

Turn the four pinned upstream repositories into a deterministic, source-backed, machine-readable capability denominator that can drive all later architecture and parity work.

The iteration succeeds when another machine can reproduce the acquisition, inventory, normalization and evidence process and obtain the same capability ledger within defined deterministic tolerances.

## Inputs

- `UPSTREAM_LEDGER.yaml`
- pinned source commits
- code
- tests/fixtures
- docs
- package/build manifests
- release/CI configuration
- current parity taxonomy

## Required outputs

```text
scripts/upstream/
scripts/inventory/
inventory/upstreams/
inventory/schemas/
reports/CP01_CAPABILITY_REPORT.md
graphs/capability_graph.json
licenses/UPSTREAM_NOTICES.md
evidence/cp01/acquisition/
evidence/cp01/baselines/
evidence/cp01/gauntlet/
ledgers/CAPABILITY_LEDGER.jsonl
```

Exact paths may evolve only through a recorded decision; do not scatter equivalent outputs across ad hoc locations.

## Subcheckpoints

See `CHECKPOINTS.md` I01.0–I01.8.

## Engineering requirements

- Reproducible pinned-source acquisition.
- Source trees stored in ignored local cache, not copied into Git during inventory.
- Deterministic inventory schemas with version fields.
- Capability records backed by code/test/doc evidence.
- Separate implemented behavior from documented/experimental/platform-gated/external-ecosystem behavior.
- Preserve extension ecosystems as capabilities.
- No manual parity percentage.
- Baseline test failures classified honestly.
- CP02 contract requirements generated from actual findings.

## Non-goals

- Writing the final Rust kernel.
- Reimplementing upstream features.
- Choosing a single model/STT/channel provider.
- UI convergence.
- Production deployment.
- Claiming behavioral parity before adapters/tests exist.

## Iteration acceptance

Iteration 01 closes only when CP01 closes with evidence and `CHECKPOINT_REGISTRY.json` advances consistently to CP02.
