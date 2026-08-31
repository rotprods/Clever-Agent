# `/empezarproyecto` — canonical project boot/recovery command

## Intent

Start or resume Clever-Agent from durable repository truth without depending on the originating chat.

This command is mandatory before material work.

---

## Invocation contract

When the operator says `/empezarproyecto` or asks to start/resume the repository, perform the following immediately. Do not ask what to work on if the persisted frontier is unambiguous.

## STEP 1 — Establish execution identity

Resolve:

- repository root;
- current branch/worktree;
- HEAD commit;
- dirty/untracked state;
- agent/runtime identity;
- session ID.

Recommended session ID:

`YYYYMMDD-<agent>-<short-random-or-head>`

Do not fabricate a clean state. If uncommitted work exists, inspect it before modifying anything.

## STEP 2 — Read authority chain

Read, in order:

1. `AGENTS.md`
2. `GOAL.md`
3. `SECURITY_MODEL.md`
4. `ARCHITECTURE.md`
5. `CAPABILITY_PARITY.md`
6. `CHECKPOINT_REGISTRY.json`
7. `CHECKPOINTS.md`
8. `STATE.md`
9. `GOAL_STATE.json`
10. `EXECUTION_STATE.json`
11. active `iterations/*/STATE.json`
12. active iteration `ITERATION.md` and `METAPROMPT.md`
13. `HANDOFF.md`
14. relevant ledgers/evidence
15. recent Git history/PR context.

## STEP 3 — Validate canonical state

Run:

```bash
python scripts/validate_agentic_state.py
```

If it fails, enter `RECONCILIATION` mode. Fix or persist the inconsistency before implementation.

## STEP 4 — Reconcile claims and unfinished work

Inspect:

```text
ledgers/WAVE_LEDGER.ndjson
ledgers/CLAIM_LEDGER.ndjson
ledgers/RUN_LOG.ndjson
HANDOFF.md
Git branches/worktrees/PRs
```

Determine:

- active waves;
- stale/incomplete claims;
- branch divergence;
- blockers;
- work that exists in Git but not state, or state not supported by Git/evidence.

Never overwrite unfinished work to make the repository look clean.

## STEP 5 — Resolve frontier

Derive exactly:

```text
GOAL
GLOBAL CHECKPOINT
ITERATION
NEXT EXECUTABLE SUBCHECKPOINT
CANDIDATE WAVE
DEPENDENCIES
REQUIRED EVIDENCE
RISKS
OWNED PATHS
```

For the current repository snapshot, expected frontier is CP01 / Iteration 01 unless persisted evidence proves otherwise.

## STEP 6 — Register session start

Append a `HELLO`/`WORK_STARTED` record to `ledgers/RUN_LOG.ndjson` before material mutation.

Minimum fields:

```json
{
  "event":"WORK_STARTED",
  "session_id":"...",
  "agent":"...",
  "checkpoint":"...",
  "iteration":"...",
  "wave_id":"... or null",
  "branch":"...",
  "head":"..."
}
```

Use a real timestamp when the environment can provide one; never invent precision.

## STEP 7 — Claim wave

If no active compatible wave is already assigned:

1. define the smallest coherent wave;
2. declare owned paths/surfaces;
3. inspect claim conflicts;
4. append claim/wave records;
5. set status `CLAIMED`, then `IN_PROGRESS` when mutation begins.

No claim → no production mutation.

## STEP 8 — Build ContextPack

Before editing, write down or materialize:

```text
session_id
wave_id
checkpoint + exit criterion
iteration/subcheckpoint
objective
known facts
assumptions to verify
inputs/dependencies
owned paths
acceptance criteria
test plan
evidence plan
security/risk considerations
exact next action
```

This ContextPack can be stored in `sessions/<session-id>/CONTEXT.md` for long/multi-agent work.

## STEP 9 — Execute

Use the loop in `AGENTS.md`:

`OBSERVE → MODEL → PLAN → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → COMMIT → RECONCILE`

Do not stop at planning when implementation is possible.

## STEP 10 — Before every material response/session exit

Persist:

- implementation changes;
- run/wave/claim state;
- decisions/risks;
- evidence;
- `STATE.md` / machine mirrors if frontier changed;
- `HANDOFF.md`.

Release or explicitly retain claims.

## Required boot output to operator

Keep it short:

```text
PROJECT:
HEAD/BRANCH:
CHECKPOINT:
ITERATION:
WAVE:
STATE VALIDATION:
CLAIMS:
FRONTIER:
FIRST ACTION:
```

Then execute the first action unless blocked.
