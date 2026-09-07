# CP03-W02-CONTROL — verified slice and publication boundary

Recorded: 2026-09-07. Parent task CP03-002 / wave CP03-W02 remains open.

## Source and evidence identity

- Canonical base: `7feba0d207413b67f6a612e81fc16c04cc4c51da` (merged planning PR #14).
- Implementation trigger: `1a52b02db91152443af2fe08b51db37e52fd2192`.
- Formatted source actually tested: `5faa1de6503687b707a6a97e2eba4c870e3ded11`.
- Source plus persisted evidence: `76a751bb58620b31948dae331c17d349d0f979b5`.
- PR: #15, draft, not merged.
- GitHub Actions run: `34149317865`, job `101828040797`, all steps SUCCESS.
- Evidence ID: `EVID-W02-CONTROL-20260907`.
- Artifact ID: `10028806532`.
- Artifact ZIP SHA256: `9e67755340940cdf2cec93439f18e599745e1620c3e6e131ec352e340774541f`.

The downloaded artifact hash and all 115 file hashes listed in its summary were independently recomputed successfully in the assistant container after local tool access recovered. No local Rust execution is claimed: Cargo was unavailable and GitHub DNS resolution failed. The runtime tests ran in GitHub Actions.

## What executed

1. 25 new Python protocol/receipt tests PASS; 7 pre-existing sidecar tests PASS.
2. Identical new Rust test conditions on historical production source: 11 expected assertion failures reproduced (RED). Build errors cannot satisfy this gate.
3. Patched source: all 15 named Rust control regressions PASS (GREEN).
4. Five repeated runs of those 15 cases: 75 executions PASS.
5. Full kernel run: suites reported 1 + 6 + 7 + 15 + 7 + 3 = 39 passing tests, zero failed/ignored. This includes the explicit real pinned OpenJarvis sidecar/registry test with 230 entries, not a real-model inference.
6. Rustfmt, Clippy, contracts/generated-manifest, parity, canonical state, subordinate plan and deterministic ContextPack checks passed.

Counts overlap: the 15 control tests also appear in the full kernel run. Do not sum executions as unique capabilities or unique tests.

## First failed attempt is retained

Run `34148878892`, artifact `10028646436`, source input `d70df0bfa9b96ca3b969449839196148b4bbc199`, stopped at the RED receipt gate. The artifact shows three genuine assertion failures whose custom messages omitted the literal marker required by the receipt parser. Commit `1a52b02...` prefixed the messages with `assertion:` without changing tested conditions or relaxing the gate. Initial failure evidence remains preserved.

## Scope proven

Request/reply correlation for control operations; poisoned connection after ambiguous timeout/protocol response; fail-closed invalid/contradictory health; decoded negotiated-frame acceptance; staged atomic registry batch validation; Python acknowledgement/recent-replay/deadline validation and fragmented prefix handling; mandatory named tests in this gate.

Not proven: global bounded I/O, full anti-replay epochs, raw-wire accounting of discarded unknown Protobuf fields, remote shutdown guarantees, inference cancellation or model/provider parity. Zero parity promotion.

## Publication restriction — STOP

During reconciliation another branch was found: `wave/cp03/w02-control-guards@fbe068e6f52c233c67f24820310d68de0f2e9fa8`. Its recovery receipt records a prior security block on CI auto-publication. This branch has not been overwritten, deleted or merged.

The current branch's successful CI run had already published source/evidence before that earlier boundary was discovered. A subsequent request to replace `.github/workflows/cp03-w02-control.yml` with a read-only workflow was itself blocked by OpenAI security controls. That update DID NOT apply. No alternate API, encoded payload, helper workflow or credential path was attempted to bypass it.

The existing workflow therefore still has its previous configuration. Do not claim it is read-only or retired. Do not trigger more automatic publication or merge this PR until an authorized maintainer resolves this workflow boundary and reviews the ordinary source diff. The PR stays draft. There is no autonomous/background continuation promised.

## Next executable work after the boundary is resolved

1. Reconcile this branch with the separate control-guards branch; compare diffs and source hashes instead of copying generated fixes blindly.
2. An authorized maintainer must establish read-only validation without automatic repository writeback. Check real repository protection/rulesets before release.
3. Revalidate the exact reviewed committed candidate, including the native OpenJarvis lane; then consider merge. This is a support-slice merge, not W02 closure.
4. Reconcile W02-00 environment evidence and compile W02-01 obligation IDs/count.
5. W02-03: aggregate queue/byte budgets, actual wire-length limits (including unknown fields), write deadlines and a responsive control path.
6. W02-04: bounded teardown, process-tree/container cleanup and watchdog regressions.
7. Complete the remaining W02-05 criteria, then inference contracts and real-model lane.

Keep global denominator 7,565, OpenJarvis obligations 646, and VERIFIED zero. Do not mark G1, W02-03/04/05, W02 or CP03 complete from this result.
