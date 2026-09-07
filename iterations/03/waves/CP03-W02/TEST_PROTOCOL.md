# W02 test / retest / refactor protocol

Status: specified, NOT executed. These are future product tests. `test_cp03_w02_plan.py` proves only plan integrity.

| Case | Fault/fixture | Required outcome |
|---|---|---|
| H01 | Interpreter/image/model missing | Mandatory lane preflight FAIL/BLOCKED; no silent return PASS. |
| H02 | Empty JUnit or required case omitted | Gate rejects; names/counts compared against requirements. |
| T01 | Flood valid maximum frames | Bound frame, queue messages and aggregate bytes. |
| T02 | Peer never reads stdin | Bounded write timeout and responsive control or teardown. |
| T03 | Partial/coalesced header/payload | Correct decode or explicit error; truncation never success. |
| T04 | Peer negotiates lower frame limit | Enforce minimum both directions after handshake. |
| T05 | Late/duplicate/foreign health/results | Request/attempt correlation prevents misdelivery. |
| T06 | Valid then invalid registry entry | No partial application or overwritten prior descriptor. |
| L01 | STOPPING without process exit | Bounded cleanup and honest terminal error. |
| L02 | Grandchild retains stdout pipe | No indefinite Drop/join; process-tree cleanup demonstrated. |
| L03 | Docker client dies but workload remains | Track container ID and verify workload removal. |
| I01 | Pinned native engine and real weights | Entire Rust→wire→sidecar→OpenJarvis→model path exercised. |
| I02 | Registered model without weights | Never SERVING; explicit availability. |
| I03 | Invalid/out-of-budget generation config | Reject before engine call; no silent option loss. |
| I04 | Stream/full stream and split UTF-8 | Ordered payload and exactly one terminal. |
| I05 | Missing usage/finish metadata | UNKNOWN, not fabricated values. |
| C01 | Cancel before/during/terminal race | One terminal; no later chunks; actual worker lifecycle checked. |
| C02 | Worker ignores cancel | Bounded forced local termination; remote effect UNKNOWN unless proved. |
| C03 | Concurrent requests/principals | No cross-delivery; isolated cancel or explicit tested single-flight BUSY. |
| O01 | Invalid structured JSON | Explicit schema/semantic failure, no fabricated correction. |
| O02 | Fragmented tool calls/malicious names | Preserve as data; zero tool execution. |
| F01 | Failure before first token | Authorized bounded retry, new attempt ID, cumulative budget. |
| F02 | Failure after partial stream | Partial/failure terminal; no stream splicing or hidden cost. |
| S01 | Unapproved endpoint/SSRF config | Kernel rejects egress; model cannot select arbitrary destinations. |
| S02 | Secret/prompt canary in errors/stderr | Redacted artifacts; no cross-principal leak. |
| S03 | Registry metadata self-grants policy/parity | Cannot change T0 authorization or VERIFIED state. |
| P01 | Direct vs adapted same-host inference | Record engine/model/config/sample count, latency/TTFT/memory/throughput. |
| P02 | Repeated race/flood/restart | Preserve all seeds/results; do not select a good rerun. |
| E01 | Forged/stale evidence SHA/model/test ID | Parity/release gate rejects. |
| E02 | Denominator edited or waiver counted VERIFIED | Reject; blocked/waived remain separate. |
| R01 | Clean rebuild and post-merge | Relevant checks on exact source; no stale green claims. |

For every significant slice: capture RED/characterization case; minimal implementation; original test; touched contract/W01 regression; security/recovery gauntlet; clean-process retest; persist command, SHA, environment, lane, executed/skipped cases, exits and hashes; reconcile task/graph/evidence before COMPLETE.

Proposed initial retest budget: 20 critical cancel/flood/teardown executions with retained seeds. This is a gate, not a statistical reliability claim. Fix latency/memory budgets before measurement against a same-host baseline; never relax after failure to obtain green.

Refactor only for unbounded/noncancelable I/O, ambiguous transitions, duplicated policy, missing atomicity or untestable coupling. Characterization tests precede refactor. Separate semantic and cosmetic changes. Re-run original regression, native integration, security, recovery, performance and clean rebuild afterwards.

Receipt fields: source_sha, upstream_commit, task/test IDs, command, lane, engine/runtime/model digests, environment fingerprint, PASS/FAIL/BLOCKED/NOT_RUN/SKIPPED, observed timestamps, exit code, required/executed/skipped cases, failure reason, artifact paths/SHA-256, finding and obligation IDs.

Keep test jobs read-only. A controlled release transaction verifies exact source/artifact provenance, case coverage and denominator before state writes. Preserve failed receipts. Retire historical state-mutating workflows. A bot commit without a successor check is not a passing successor build.
