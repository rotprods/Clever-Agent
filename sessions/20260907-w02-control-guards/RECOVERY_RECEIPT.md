# W02 control guards — recovery receipt

Recorded: 2026-09-07. Scope: CP03-W02-CONTROL-01, not full CP03-W02 or inference parity.

## Durable starting point

Planning PR #14 was merged as `7feba0d207413b67f6a612e81fc16c04cc4c51da`. The canonical frontier remains CP03-002 / CP03-W02.

## Executed evidence

GitHub Actions run `34146223914`, job `101818732497`, source input `a426de1e7f7a379aaf607f1264d279c9aa2c71b6`:

- The control gate observed 13 expected failing regression cases and two passing controls before applying the scoped repair.
- After the repair, all 15 control tests passed, followed by a second successful 15-test run.
- The mandatory native OpenJarvis registry test passed separately. This exercises the pinned native runtime, not a model inference.
- Rust regression and Clippy, Python gate/sidecar tests, planning and context/ledger checks passed in that job.
- The overall workflow FAILED at the publication scope guard, before its generated commit was pushed. Git porcelain collapsed an untracked evidence directory, which the guard rejected.

Preserved artifact: `10027758311`, `w02-control-red-green-a426de1e7f7a379aaf607f1264d279c9aa2c71b6`, ZIP SHA-256 `961db2e86a6068a7dc6b122ff777550a39fdaf1d76e209f1ed1c1dc16677cab7`.

The evidence identifies post-repair subject hashes. The input commit MUST NOT be described as containing the repaired production files. Tests executed against an ephemeral repaired worktree.

## Publication boundary

An attempted update to the automatic CI publication workflow was blocked by a security control. That mechanism was retired: `.github/workflows/cp03-w02-control-repair.yml` was deleted in `7e2d53eee6b5837ebc5a7fcaa54e0ff672aaa0cf`. Do not recreate an automatic write-token publication path to bypass this boundary.

The follow-up candidate `c0384ebc29041fa5c3c1d547ff749bb269749e6c` uses read-only validation and a source/evidence artifact. It additionally targets actual received wire-byte accounting when Protobuf unknown fields are discarded during decoding. Treat this refinement as requiring its own observed CI evidence; do not inherit the first run's PASS onto changed source.

## Remaining work

1. Inspect the exact read-only candidate run and its source/evidence artifact.
2. Verify subject hashes, review the ordinary source diff, and persist tested production files through a normal reviewed PR without CI auto-publication.
3. Re-run read-only checks on the actual committed candidate before merge.
4. Reconcile claims, subordinate task statuses, evidence and ContextPack from the proven state.
5. Continue W02 obligation selection and bounded I/O/lifecycle work.

Still NOT complete: bounded aggregate queue, bounded writes and teardown, container/process-tree cleanup, effective inference cancellation, real generation/streaming, full W02 obligation parity and release governance.

Global denominator 7,565; OpenJarvis obligations 646; no capability parity promotions are authorized by this receipt. Do not close W02 or advance to W03 from this control-plane test result.
