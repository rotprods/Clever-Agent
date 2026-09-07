# CP03-W02-CONTROL — scoped implementation session

Source: 7feba0d207413b67f6a612e81fc16c04cc4c51da; PR14 already merged.
Parent: CP03-002 / CP03-W02. Claim: CLAIM-W02-CONTROL-20260907.
Session event: WORK_STARTED. Local container/Python tools returned ClientError; execution uses GitHub Actions, not an unverified local PASS.

This slice implements control correlation, poisoned-connection fail-closed behavior, registry batch atomicity, negotiated frame acceptance, Python acknowledgement/replay/deadline checks and a mandatory named-test harness. It does not close W02-03/04/05 or a global checkpoint and adds no dependency.

RED compares identical new test sources against the original source pin. GREEN and repeated GREEN must exercise named cases under an external watchdog; build errors and empty/skipped results cannot satisfy RED or GREEN.

A native pinned OpenJarvis container replay must still enumerate 230 entries and complete control lifecycle. That replay is not real-model inference. No side effects, model download or provider credential use is permitted.

Remaining blockers: aggregate queue bound; write and teardown deadlines; process-group/container-ID cleanup; full anti-replay epochs; stderr redaction/bounds; mandatory interpreter enforcement when bypassing the gate; inference contracts; model lane. Main protection currently reports false; administration remains an external requirement, not waived.

COS20D focus: D01_PROVENANCE_EVIDENCE, D03_CAPABILITY_SEMANTICS, D05_RUNTIME_OWNERSHIP, D06_INTERFACE_CONTRACTS, D07_STATE_DATA, D10_LIFECYCLE_CONCURRENCY, D12_SECURITY_PERMISSION, D13_FAILURE_RECOVERY, D15_TEST_EVAL_PARITY, D19_TEMPORAL_DRIFT.

No changes to CAPABILITY_LEDGER, PARITY_LEDGER, upstream pins, or global frontier. Generated ContextPack must be regenerated after claim/evidence changes. Runtime tests and capability parity must never be confused.
