---
name: empezarproyecto
description: Boot or resume Clever-Agent from durable repository truth, reconcile state and claims, and start the next valid wave.
---

# Empezar proyecto

Execute the canonical project boot/recovery protocol in `commands/EMPEZARPROYECTO.md`.

Requirements:

1. Treat `AGENTS.md` as the authoritative execution contract.
2. Reconcile Git, state, iteration, handoff, ledgers, evidence and claims before material edits.
3. Run `python scripts/validate_agentic_state.py` when the environment permits.
4. Resolve the exact active checkpoint/iteration/wave from durable state rather than chat memory.
5. Append the required session start/run records and claim the wave before production mutation.
6. Build the ContextPack and then **execute the first unblocked action**; do not stop at a generic plan.
7. Persist evidence/state/handoff before ending.

If the repository is inconsistent, enter reconciliation mode and repair/persist the discrepancy before implementation.

After boot, report only the compact boot header defined by `commands/EMPEZARPROYECTO.md`, then continue execution.
