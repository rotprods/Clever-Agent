# `/graphify` — source evidence to semantic surface projection

## P0 raw evidence

`repository_graph` v1 remains the deterministic source-evidence representation. Do not mutate its schema or IDs merely to improve a downstream classification.

## P1 Graphify V2

```bash
python -m scripts.graphify.v2 <repository_graph.json> --output <semantic_surface_projection.json>
```

Graphify V2 emits compact candidates for registered/executable surface families while preserving source path/commit/line evidence.

Every output surface starts:

```text
promotion_status = DISCOVERED_CANDIDATE
behavioral_evidence_required = true
```

A lexical/structural match is never automatically a capability. W03 must attach registration/protocol/runtime evidence; W04 owns canonical capability normalization.

## Prohibited

- counting raw files/functions/classes as parity;
- deleting P0 nodes during deduplication;
- merging by name/description similarity;
- using Graphify output to authorize migration.
