---
name: empezarproyecto
description: Boot or resume Clever-Agent from durable graph/state truth, reconcile ContextPack and claims, and execute the next valid wave.
---

# Empezar proyecto

Execute `commands/EMPEZARPROYECTO.md` exactly; do not fork policy.

Requirements:

1. `AGENTS.md` is authoritative.
2. Reconcile Git, state, `.agentic/CONFIG.yaml`, ContextPack, HANDOFF, ledgers, evidence and claims.
3. Run state validator, context validator and ContextPack `--check`.
4. Load `.agentic/context/COS20D.json` and identify dimensions touched.
5. Resolve frontier from durable truth rather than chat memory.
6. Register session/claim before production mutation.
7. Execute `/cos-graph-engineV2`; do not stop at a generic plan when implementation is possible.
8. Persist evidence/state/HANDOFF, regenerate ContextPack and validate before ending.

If inconsistent, reconcile first. After boot report the compact header from the canonical command and continue execution.
