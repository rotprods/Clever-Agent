# `/empezarproyecto` — canonical project boot/recovery command

## Intent

Start or resume Clever-Agent from durable repository truth without depending on the originating chat. Mandatory before material work.

## STEP 1 — Execution identity

Resolve repository root, branch/worktree, HEAD, dirty/untracked state, agent/runtime identity and session ID. Never fabricate a clean state.

## STEP 2 — Authority chain

Read in order:

1. `GOAL.md`
2. `SECURITY_MODEL.md`
3. `AGENTS.md`
4. `ARCHITECTURE.md`
5. `CAPABILITY_PARITY.md`
6. `docs/COS_GRAPH_ENGINE_V2.md`
7. `docs/GRAPH_ENGINEERING_PROTOCOL.md`
8. `CHECKPOINT_REGISTRY.json`
9. `CHECKPOINTS.md`
10. `STATE.md`
11. `GOAL_STATE.json`
12. `EXECUTION_STATE.json`
13. active iteration `STATE.json`, `ITERATION.md`, `METAPROMPT.md`
14. `.agentic/context/CURRENT_CONTEXT.json`
15. `HANDOFF.md`
16. relevant ledgers/evidence and recent Git/PR history.

The ContextPack is derived and never outranks canonical Git/state/evidence.

## STEP 3 — Validate state + context

Run:

```bash
python scripts/validate_agentic_state.py
python scripts/context/validate_context_pack.py
python scripts/context/build_context_pack.py --check
```

If any fails, enter `RECONCILIATION`. Do not implement on contradictory state.

## STEP 4 — Reconcile claims and unfinished work

Inspect wave/claim/run ledgers, HANDOFF, branches/worktrees/PRs and CI evidence. Determine active parent waves, support subwaves, stale claims, branch divergence, blockers and Git/state mismatches. Never overwrite unfinished work to manufacture cleanliness.

## STEP 5 — Resolve exact frontier

Derive:

```text
GOAL
CHECKPOINT
ITERATION
SUBCHECKPOINT
NEXT EXECUTABLE WAVE
ACTIVE SUPPORT SUBWAVES
DEPENDENCIES
REQUIRED EVIDENCE
OPEN RISKS
OWNED PATHS
GRAPH INPUTS/OUTPUTS
```

Do not assume a hard-coded frontier.

## STEP 6 — Register session start

Append `WORK_STARTED` to `ledgers/RUN_LOG.ndjson` before material mutation with session/agent/checkpoint/iteration/wave/branch/HEAD.

## STEP 7 — Claim wave

If not already assigned a compatible claim:

1. define the smallest coherent wave/support subwave;
2. declare paths/surfaces and graph inputs/outputs;
3. conflict-check active claims;
4. append claim/wave record;
5. move `CLAIMED → IN_PROGRESS`.

No claim → no production mutation. Scope expansion requires a claim amendment before touching new canonical surfaces.

## STEP 8 — Load 20D focus

Read `.agentic/context/COS20D.json`. Select dimensions materially affected by the wave. At minimum every major decision considers D00 mission, D01 evidence, D03 semantics, D05 ownership, D06 interfaces, D15 tests/parity and D19 drift, plus family-specific security/state/failure/device dimensions.

Do not copy all 20 dimensions onto raw source nodes.

## STEP 9 — Build/verify ContextPack

`CURRENT_CONTEXT.json` must expose frontier, exact pins, graph planes, hard invariants, claim/risk/decision/evidence IDs and recovery commands.

If canonical state changed:

```bash
python scripts/context/build_context_pack.py
python scripts/context/validate_context_pack.py
```

## STEP 10 — Execute `/cos-graph-engineV2`

Use:

`BOOT_RECONCILE → OBSERVE → GRAPHIFY → MODEL → CROSS_LINK → PROJECT_20D → DECIDE → PLAN_COMPILE → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → AUTOPROMPT_REFLECT → COMMIT_RECONCILE`

Do not stop at planning when implementation is possible.

## STEP 11 — Before every material exit

Persist implementation, claims/waves, decisions/risks, evidence, state mirrors, HANDOFF and graph/context deltas. Regenerate ContextPack and run all validators. Release or explicitly retain claims.

## Required boot output

```text
PROJECT:
HEAD/BRANCH:
CHECKPOINT:
ITERATION:
WAVE:
SUPPORT WAVES:
STATE VALIDATION:
CONTEXT VALIDATION:
CLAIMS:
20D FOCUS:
FRONTIER:
FIRST ACTION:
```

Then execute the first action unless blocked.
