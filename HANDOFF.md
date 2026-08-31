# HANDOFF — Clever-Agent

## Identity

- Project: `CLEVER-JARVIS-001`
- Global checkpoint: `CP01 — Forensic upstream inventory`
- Iteration: `I01 — Forensic Capability Compiler`
- Completed: `I01-W00`, `I01-W01`
- Active frontier: `I01-W02 — Structural inventory`
- Support subwave: `I01-W02-CTX — COS Graph Engine V2 / 20D context + regression/planning integrity`
- Capability denominator: `NOT_GENERATED`
- PR: `#4` (draft until final gates are green)

## Where we came from

The project evolved from “merge four agent repos” into a governed evidence compiler:

`P0 source evidence → P1 semantic/behavioral surfaces → P2 COS20D provisional decisions → P3 future-agent context`.

OpenJarvis supplies strong cognitive typing; OpenClaw supplies contribution/lifecycle/rollback semantics; Omi supplies ambient/episodic/device lifecycle; Clicky supplies native macOS embodiment. The target remains federated/polyglot until behavioral parity proves a narrower convergence safe.

Read first:

1. `docs/ACTA_DE_CONSCIENCIA.md`
2. `docs/REGRESSION_2026-08-31.md`
3. `IMPLEMENTATION_PLAN.md`
4. `TASKS.md`
5. `.agentic/context/NEXT_ACTIONS.json`
6. `.agentic/context/CURRENT_CONTEXT.json`

## Proven evidence

W01 full four-upstream forensic run `33402789051` / job `99522924366` succeeded on exact pinned sources. Artifact `9762075538`, digest `sha256:f09dbec5fd39dbb97c56e8a3c986602a6b260adefb49f34a08aed791fc8fe6bc`.

It proved exact-SHA acquisition, immutable pin verification, source-only projections, four Graphify outputs and non-destructive COS hypergraph generation.

Raw graph size: 1,179,885 evidence nodes / 1,181,257 edges / 139 provisional component groups / 110 provisional cross-repo groups. These are **not capability counts**.

Graphify/COS and Agentic Contract also passed on V2 commit `a9d6fa0ed60e079dcb345e9e8f923bbf5519c98e`.

## Regression findings now fixed/in verification

### 1. W02 performance contradiction

Run `33403318373`, job `99524692283`, reached acquisition + pin verification successfully. `Compile structural inventories from complete Git trees` ran ~19m55s then was cancelled by the 20-minute job timeout.

Root cause: `git ls-tree -l` requested every blob size against `blob:none` partial clones. This could lazily resolve/fetch blobs and defeated the acquisition architecture.

Fix in current candidate: structural inventory uses tree metadata only; blob `size` remains `null` and tests enforce this.

### 2. ContextPack memory ghosting

Regression found `CURRENT_CONTEXT.json` referencing D-0006..D-0009 / RISK-0004 before those IDs existed in canonical ledgers.

Fix in current candidate:

- D-0006..D-0010 and RISK-0004..RISK-0005 are persisted;
- ContextPack rebuilt from ledgers/state;
- orphan ID checks added;
- deterministic ContextPack check added;
- executable task DAG added and validated;
- Agentic Contract runs all state/context/plan gates.

## Exact current execution order

Machine authority: `.agentic/context/NEXT_ACTIONS.json`.

Immediate gates:

1. `CTX-001` — verify ledger/context reconciliation.
2. `CTX-002` — verify CI context gate.
3. `CTX-003` — verify executable task DAG.
4. `W02-001` — verify blobless structural scanner.
5. `W02-002` — successful final-head four-source structural workflow.
6. Persist W02 evidence and close I01.2.
7. Only then enter W03 behavioral surface extraction.

## W03 direction after W02 closes

Prioritize explicit registered/executable behavior, not lexical names:

- OpenJarvis typed registries and registrations;
- OpenClaw plugin registrars / gateway / session / lifecycle surfaces;
- Omi FastAPI router topology, listen runtime, STT/TTS, conversations/memory, reconciliation and device surfaces;
- Clicky Swift PTT/screen/TTS/overlay/pointing + worker/proxy boundaries.

W03 outputs candidates/BEHAVIOR_MAPPED surfaces. W04 builds the actual capability denominator. No Clever capability becomes `VERIFIED` just because upstream implements it.

## Recovery commands

```bash
python scripts/validate_agentic_state.py
python scripts/context/validate_next_actions.py
python scripts/context/validate_context_pack.py
python scripts/context/build_context_pack.py --check
```

Then execute `/empezarproyecto` and the first executable task from `NEXT_ACTIONS.json`.

## Hard stop conditions

- Do not close W02 without successful final-head artifact/evidence.
- Do not start denominator compilation before W03 completeness review.
- Do not implement final CP02 kernel contracts before CP01 closes.
- Do not authorize state/code migration from provisional COS decisions.
