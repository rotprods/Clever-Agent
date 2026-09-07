# W02 scope compiler — executed allocation, not inference parity

Parent: CP03-002 / W02-01. Support slice: CP03-W02-SCOPE-20260907. Tracking: issue #16.
Base: main `7feba0d207413b67f6a612e81fc16c04cc4c51da`. No PR #15, workflow, runtime, source-ledger or checkpoint changes.

## Executed result

The compiler checked all 7,565 source obligations, joined 646 OpenJarvis obligations one-to-one to their behavior surfaces, and checked source-file membership against the 2,108-entry pinned inventory. Three input files match connected GitHub Git-blob identities and local SHA-256 locks.

Allocation is deliberately PROVISIONAL: **32 W02 core proposals + 52 shared/facet reviews + 562 retained for other CP03 waves = 646**. The 562 are not waivers or exclusions. `K_final` remains null. All 2,188 candidate definitions stay outside the denominator; 119 are attached as supplemental source-review work.

`family == inference` alone selects 64 records but misses 20 records this conservative scope treats as relevant. It also catches connector/ingest and unresolved router-mount records. Example: `cap_56358709cbc328e25ed1afff`, POST /v1/chat/completions, is classified `api_protocol` in CP01. The pinned implementation invokes memory and may dispatch to an agent; it must be split into behavioral facets rather than claimed fully verified by a direct engine test.

All 29 mount records are review items because CP01 does not preserve enough router-target/prefix detail. The allocation view is not a complete call graph and does not prove completeness of CP01's capability ontology.

## Additional code-level audit

AST inspection of exact OpenJarvis `_stubs.py` blob `cd7dc0d4cc16d54058caa9af492f70d4b0ef76b2` maps eight engine methods and the six StreamChunk fields. Seven methods were not represented as individual surface records in the supplied CP01 projection. This does not mean the upstream lacks those methods; it is a granularity gap in the derived inventory.

Important contract requirements:

- `can_serve` defaults to True; it cannot establish model installation/readiness.
- Base `stream_full` wraps `stream` and emits `finish_reason=stop`. Distinguish upstream-synthetic termination from a provider-observed reason. Check concrete overrides before asserting rich-tool-stream support.
- `close` and `prepare` have no-op default bodies. Presence does not prove cleanup/warmup.
- `generate`, `stream`, `list_models`, and `health` are abstract requirements, not executed provider implementations.
- StreamChunk: content, tool_calls, finish_reason, usage, content_blocks, tool_results. Structured output: type and schema.

## Reproduce (Python standard library; no upstream installation)

```sh
python scripts/cp03/w02_scope.py --write
python -m unittest discover -s tests -p 'test_cp03_w02_scope.py' -v
python scripts/cp03/w02_scope.py --check
```

`--write` generates the full allocation JSONL, supplemental candidates, grouped IDs and graph. They are deterministic derived views; source ledger remains immutable. Summary and contract audit are retained in Git; the full generated data is also in the delivered evidence package and can be recreated without chat memory.

Optional actual-source audit, from an exact pinned OpenJarvis checkout:

```sh
python scripts/cp03/w02_scope.py --source-root /path/to/pinned/OpenJarvis --write
python scripts/cp03/w02_scope.py --source-root /path/to/pinned/OpenJarvis --check
```

No source import, model call, install hook or network request is executed. The input source blob must match the pinned tree.

`--require-frozen` returns nonzero without writing: this version cannot self-approve an unresolved scope. `--check` proves generated-byte consistency, NOT semantic approval or runtime parity.

## Test/retest evidence

First compiler pass: 35 tests, three failing assertions (boolean schema/zero accepted as integers and an overridable canonical pin). Minimal fixes added strict type checks and canonical pins. Expanded final suite: **51 passed**, then **51 passed again**, including 12 AST contract tests. Model/runtime inference tests: zero. Tests and failures are retained in the session evidence package; file identities are in `sessions/20260907-w02-scope/VERIFICATION.json`.

## Exact next work

1. Review each shared/facet record, beginning with chat/ask/serve, 29 router mounts, and mislabeled connectors. Assign facet ownership without removing capability IDs.
2. Map all eight engine methods to contract fields and planned behavioral tests; do not count seven syntax discoveries as newly VERIFIED capabilities.
3. Decide whether candidate granularity requires an explicit CP01 correction transaction. This slice does not authorize one.
4. Only then freeze K and close W02-01 through canonical gates. W02-03/04 transport hardening and the PR #15 publication boundary remain independent blockers.

No capability promotion, migration authorization, scope waiver, CI permission change or global state transition occurred here.
