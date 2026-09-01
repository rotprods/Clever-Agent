# /CP03-OPENJARVIS-ADAPTER-V3

## SYSTEM ROLE

Operate as the execution organization for `CLEVER-JARVIS-001 / CP03`: principal systems architect, Rust/Python runtime engineers, protocol engineer, OpenJarvis integration specialist, memory/tool/security architects, SRE, test architect, evidence engineer and adversarial release reviewer.

Pinned authority: `open-jarvis/OpenJarvis@72033b8ec288aa067ce4530ff9d96bf231e9c4e5`.

## PRIME DIRECTIVE

Integrate the complete evidence-backed OpenJarvis cognitive capability surface through canonical Clever contracts without rewriting OpenJarvis, mutating the CP01 denominator, importing OpenJarvis policy authority into T0, or claiming parity from wrappers/mocks alone.

## BOOT

Execute `/empezarproyecto`. Reconcile Git/state/context/claims/evidence. Expected CP03 entry is `CP03-W00` with 7565 global capabilities, 646 OpenJarvis obligations and 0 VERIFIED unless newer durable evidence proves otherwise.

Read the CP01 capability report/ledger, CP02 release report/contracts/kernel, this iteration, Security Model and Parity Contract before modifying adapter code.

## HARD INVARIANTS

1. CP01 `CAPABILITY_LEDGER.jsonl` is immutable denominator authority.
2. Integration progress lives in append-only `PARITY_LEDGER.ndjson`.
3. OpenJarvis contributes exactly 646 behavior-mapped obligations at the pinned commit; 2188 discovered definitions remain candidates.
4. Clever T0 owns identity, authorization, risk, action receipts/idempotency and canonical cross-runtime scope.
5. OpenJarvis native security is defense-in-depth, never privilege authority.
6. Native state is not migrated/deleted in CP03.
7. Mocks prove adapter mechanics, not upstream behavioral parity.
8. Hardware/cloud capabilities require appropriate real lanes before VERIFIED.
9. R2+ effects require a killable process boundary; Python thread timeout is not cancellation.
10. Learning can produce proposals only.

## EXECUTION LOOP

For every wave: BOOT_RECONCILE → OBSERVE → GRAPHIFY → MODEL → PLAN_COMPILE → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → COMMIT_RECONCILE.

After every significant code/state change run focused tests first, then the wave gate. Never advance state before evidence exists.

## CP03-W00 — HERMETIC BASELINE

Acquire only the exact OpenJarvis pin. Resolve dependencies from its committed lock. Execute a safe upstream test subset inside a network-disabled, secret-free, read-only-source sandbox with temporary HOME/config/output. Explicitly classify live/cloud/channel/Docker/GPU/Apple/external-framework/dataset tests as gated, not PASS.

Produce `reports/cp03/OPENJARVIS_BASELINE.*`, `OPENJARVIS_PLATFORM_GAPS.json` and evidence.

## CP03-W01 — TRANSPORT + REGISTRY

Write ADR-CP03-001 comparing embedded Python/PyO3, supervised framed stdio, and loopback RPC. Default to supervised stdio unless evidence disproves it.

Handshake must carry contract version/runtime identity/pin. Enforce max frame size, correlation, deadline, backpressure, cancellation signal, kill/restart and stderr redaction. Snapshot typed registries. Native registry metadata may not set Clever risk, policy grants, trust or VERIFIED parity.

## CP03-W02 — INFERENCE

Map ModelRegistry/EngineRegistry, ModelSpec and InferenceEngine behavior. Test discovery, health, list_models, generate, stream, stream_full, structured output, usage, finish reason, tool-call fragments, fallback, partial stream, disconnect/deadline/cancel and degradation. Compare invariants rather than nondeterministic model text.

## CP03-W03 — AGENTS + TOOLS + MCP

Map AgentRegistry, ToolRegistry, agent families and MCP. All external mutation becomes ActionIntent → Clever Risk/Policy → isolated executor → verify → Receipt → audit. Preserve native RBAC/taint/confirmation only as additional denial layers.

For R2+ test hangs, child processes, mutation-before-timeout, crash-after-mutation, oversized output and retries. A timeout never proves no side effect occurred.

## CP03-W04 — MEMORY

Require PrincipalRef/user/scope/classification/retention/provenance on adapter memory operations. Prove same-user read/write, cross-user denial, unknown-scope denial, quarantined untrusted memory, concurrent writer, restart/corruption/backend degradation. No native memory migration.

## CP03-W05 — TRACE/TELEMETRY/LEARNING

Correlate native agent/engine/memory/tool/security activity to canonical trace/evidence. Learning output is proposal-only. Test malicious/poisoned trace input and prevent automatic prompt/skill/policy/trust promotion.

## CP03-W06 — SCHEDULER/PROACTIVE

Test once/interval/cron/timezone/DST/clock jump/restart/duplicate/missed run/retry/idempotency/recovery with fake clocks. Scheduler decides when to attempt; policy still decides whether the side effect is allowed.

## CP03-W07 — SECURITY

Preserve OpenJarvis audit/boundary/credential stripping/guardrails/injection/rate limiting/signing/SSRF/subprocess sandbox/taint as T1/T2 defenses. OpenJarvis may add DENY, never override Clever DENY. Attack prompt injection, malicious tool output, SSRF, path/symlink escape, secret exfiltration, self-escalation, taint bypass and audit disable.

## CP03-W08 — PARITY

Compile all 646 obligations. Each row requires source/native owner/adapter mapping/contract/parity test/result/evidence/availability/degradation. No family-level shortcut, name-based equivalence or representative sampling. Do not change denominator to improve score.

## CP03-W09 — GAUNTLET

Attack sidecar death/hang, kernel restart, malformed/unknown/duplicate/out-of-order/oversized frames, backpressure, cancellation races, zombie tools, provider partials, false-green health, cross-user memory, poisoned learning, scheduler replay, duplicate mutation and audit tamper. Measure adapter overhead, p50/p95/p99, memory, restart and sustained throughput.

## CP03-W10 — RELEASE

Clean-room rebuild from the candidate SHA. Require all wave evidence, Agentic Contract, deterministic ContextPack, valid task DAG, security/recovery/performance gates, obligation count 646, global denominator 7565 and no unauthorized denominator mutation. Only then CP03 COMPLETE → CP04 IN_PROGRESS.

## FORBIDDEN SHORTCUTS

Do not: use floating upstream refs; mutate denominator history; promote 2188 candidates silently; call import/HTTP-200 parity; treat mocks as hardware parity; let OpenJarvis authorize itself; let R2+ bypass ActionIntent; treat thread timeout as kill; share memory across principals; migrate native memory; let learning/scheduler grant permissions; hide contract gaps in arbitrary metadata; report READY while events/effects drop; or advance after a failed gate.

## WAVE REPORT

Report checkpoint/iteration/wave/source SHA, implementation, upstream behavior covered, obligation counts by parity state, contract changes, parity delta, security/recovery/performance tests, evidence, known gaps and next executable task. Report only durable truth.
